package service

import (
	"BugBuster/SeedD/internal/logging"
	"BugBuster/SeedD/internal/runtime"
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"sync"

	"github.com/google/uuid"
	"go.uber.org/zap"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

const (
	CallLogFile = "/tmp/callgraph.log"
)

// CallGraph represents a directed graph of function calls
type CallGraph struct {
	mu    sync.RWMutex
	nodes map[string]map[string]struct{} // caller -> set of callees
}

// Call represents a single call in the call log
type Call struct {
	ThreadID   int
	CalleeName string
	CallerName string
}

// NewCallGraph creates and initializes a new CallGraph
func NewCallGraph() *CallGraph {
	return &CallGraph{
		nodes: make(map[string]map[string]struct{}),
	}
}

// dryRunSeeds executes each seed file with the harness binary to collect call graph information
// Sets EXPORT_CALLS=1 environment variable for each run
func (s *RunSeedsService) dryRunSeeds(harnessBinary string, seedsPaths []string) error {
	s.callGraphUpdateMutex.Lock()
	defer s.callGraphUpdateMutex.Unlock()

	logger := logging.Logger
	logger.Info("Dry running seeds",
		zap.String("harness_binary", harnessBinary),
		zap.Int("seeds_count", len(seedsPaths)),
	)

	// Run the harness binary with EXPORT_CALLS=1 to collect call graph
	// The unified binary has both coverage and callgraph instrumentation
	args := []string{"-timeout=3"}
	args = append(args, seedsPaths...)
	callgraphBinary := filepath.Join(artifactDir, harnessBinary)
	cmd := exec.Command(callgraphBinary, args...)
	cmd.Dir = artifactDir
	cmd.Env = append(os.Environ(), "EXPORT_CALLS=1")
	var stdout, stderr strings.Builder
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	runErr := cmd.Run()
	logger.Info("Callgraph dry run result",
		zap.String("binary", callgraphBinary),
		zap.Error(runErr),
		zap.Int("exit_code", cmd.ProcessState.ExitCode()),
		zap.String("stdout_tail", truncateTail(stdout.String(), 500)),
		zap.String("stderr_tail", truncateTail(stderr.String(), 500)),
	)

	// Check if call log was produced
	if _, err := os.Stat(CallLogFile); os.IsNotExist(err) {
		logger.Warn("Call log file not produced by dry run",
			zap.String("expected_path", CallLogFile),
			zap.String("binary", callgraphBinary),
		)
	}

	if _, exists := s.callGraphs[harnessBinary]; !exists {
		s.callGraphs[harnessBinary] = NewCallGraph()
	}
	s.callGraphs[harnessBinary].Update()

	// Log graph stats and node names for debugging
	nodeCount := len(s.callGraphs[harnessBinary].nodes)
	nodeNames := make([]string, 0, nodeCount)
	for name := range s.callGraphs[harnessBinary].nodes {
		nodeNames = append(nodeNames, name)
	}
	logger.Info("Call graph built",
		zap.String("harness_binary", harnessBinary),
		zap.Int("node_count", nodeCount),
		zap.Strings("nodes", nodeNames),
	)

	// let's check if LLVMFuzzerTestOneInput is in the call graph
	if _, exists := s.callGraphs[harnessBinary].nodes["LLVMFuzzerTestOneInput"]; !exists {
		logger.Warn("LLVMFuzzerTestOneInput not found in call graph",
			zap.String("harness_binary", harnessBinary),
		)
		// copy CallLogFile for debugging
		logDir := os.Getenv("OSS_CRS_LOG_DIR")
		if logDir == "" {
			logDir = "/shared"
		}
		uuid := uuid.New()
		if err := copyFile(CallLogFile, fmt.Sprintf("%s/callgraph_%s.log", logDir, uuid)); err != nil {
			logger.Warn("Failed to copy callgraph log",
				zap.Error(err),
			)
		}
	}

	logger.Info("Dry run seeds completed",
		zap.String("harness_binary", harnessBinary),
		zap.Int("seeds_count", len(seedsPaths)),
	)
	return nil
}

func (s *RunSeedsService) GetCallGraph(ctx context.Context, req *runtime.GetCallGraphRequest) (*runtime.GetCallGraphResponse, error) {
	logger := logging.Logger.With(
		zap.String("harness_binary", req.HarnessBinary),
	)
	callGraph := s.callGraphs[req.HarnessBinary]
	nodes := callGraph.Export()
	jsonData, err := json.Marshal(nodes)
	if err != nil {
		logger.Error("Failed to serialize call graph to JSON",
			zap.String("harness_binary", req.HarnessBinary),
			zap.Error(err),
		)
		return nil, status.Errorf(codes.Internal, "failed to serialize call graph to JSON: %v", err)
	}
	response := &runtime.GetCallGraphResponse{
		CallGraph: string(jsonData),
	}
	return response, nil
}

// isStdFunction checks if a function name is from the standard library or other functions to exclude.
func isStdFunction(funcName string) bool {
	patterns := []string{
		"std::",
		"__gnu_cxx::",
		"operator new",
		"operator delete",
		"__cxa",
	}
	for _, pattern := range patterns {
		if strings.Contains(funcName, pattern) {
			return true
		}
	}
	return false
}

// Update parses the call log and updates the call graph.
// Format: <tid>|<callee_name>|<caller_name>
func (cg *CallGraph) Update() error {
	cg.mu.Lock()
	defer cg.mu.Unlock()

	file, err := os.Open(CallLogFile)
	if err != nil {
		return fmt.Errorf("opening call log: %w", err)
	}
	defer file.Close()

	calls, err := parseCallLog(file)
	if err != nil {
		return fmt.Errorf("parsing call log: %w", err)
	}

	return cg.processCalls(calls)
}

// Export returns a thread-safe snapshot of the call graph
func (cg *CallGraph) Export() map[string][]string {
	cg.mu.RLock()
	defer cg.mu.RUnlock()

	nodes := make(map[string][]string, len(cg.nodes))
	for caller, callees := range cg.nodes {
		nodes[caller] = mapToSlice(callees)
	}
	return nodes
}

// addCall adds a caller-callee relationship to the call graph
func (cg *CallGraph) addCall(caller, callee string) {
	if _, exists := cg.nodes[caller]; !exists {
		cg.nodes[caller] = make(map[string]struct{})
	}
	cg.nodes[caller][callee] = struct{}{}
}

// parseCallLog reads the call log file and returns a list of calls
func parseCallLog(file *os.File) ([]Call, error) {
	var calls []Call

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := scanner.Text()
		// Parse the line: <tid>|<callee_name>|<caller_name>
		parts := strings.Split(line, "|")
		if len(parts) != 3 {
			continue // skip malformed lines
		}

		threadID, err := strconv.Atoi(parts[0])
		if err != nil {
			continue // skip if threadID is not an integer
		}
		calleeName := parts[1]
		callerName := parts[2]

		calls = append(calls, Call{
			ThreadID:   threadID,
			CalleeName: calleeName,
			CallerName: callerName,
		})
	}

	if err := scanner.Err(); err != nil {
		return nil, err
	}

	return calls, nil
}

// processCalls processes the list of calls and updates the call graph
func (cg *CallGraph) processCalls(calls []Call) error {
	callsPerThread := make(map[int][]Call)
	for _, call := range calls {
		callsPerThread[call.ThreadID] = append(callsPerThread[call.ThreadID], call)
	}

	for _, threadCalls := range callsPerThread {
		callerOf := make(map[string]string)

		for _, call := range threadCalls {
			caller := call.CallerName
			callee := call.CalleeName

			callerIsStd := isStdFunction(caller)
			calleeIsStd := isStdFunction(callee)

			if !calleeIsStd && !callerIsStd {
				// Both callee and caller are user-defined
				cg.addCall(caller, callee)
			} else if !callerIsStd && calleeIsStd {
				// Caller is user-defined, callee is standard
				// In this case, we log the caller for future tracking
				callerOf = make(map[string]string)
				callerOf[callee] = caller
			} else if calleeIsStd && callerIsStd {
				// Both callee and caller are standard
				// In this case, we just propagate the caller (caller of the caller)
				if parent_caller, exists := callerOf[caller]; exists {
					callerOf[callee] = parent_caller
				}
			} else if callerIsStd && !calleeIsStd {
				// Caller is standard, callee is user-defined
				// In this case, we add the parent caller to the call graph
				if parent_caller, exists := callerOf[caller]; exists {
					cg.addCall(parent_caller, callee)
				} else {
					fmt.Println("No parent caller found for callee:", callee)
				}
			}
		}
	}

	return nil
}

// truncateTail returns the last n bytes of a string
func truncateTail(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return "..." + s[len(s)-n:]
}

// mapToSlice converts a map to a slice of strings
func mapToSlice(m map[string]struct{}) []string {
	keys := make([]string, 0, len(m))
	for key := range m {
		keys = append(keys, key)
	}
	return keys
}
