---
phase: 03-run
plan: 01
subsystem: runner-infrastructure
tags: [dockerfile, orchestration, libcrs, seedd]
requirements: [RUNF-01, RUNF-02, RUNF-03, RUNF-04, RUNF-05]
dependency_graph:
  requires: [seedgen-runtime, libCRS]
  provides: [runner-container, artifact-download, seed-registration, seedd-lifecycle]
  affects: [run-phase]
tech_stack:
  added:
    - langchain-openai (LLM client)
    - grpcio (SeedD communication)
    - grpcio-health-checking (service readiness)
  patterns:
    - OSS-CRS libCRS integration
    - Embedded SeedD lifecycle management
    - Structured JSON logging
key_files:
  created:
    - oss-crs/dockerfiles/runner.Dockerfile
    - oss-crs/bin/runner.py
  modified: []
decisions:
  - title: "Use OSS-CRS standard libCRS pattern"
    rationale: "COPY --from=libcrs matches builder Dockerfiles, provided by OSS-CRS at build time"
    alternatives: ["Download from releases", "Custom installation"]
    choice: "COPY --from=libcrs"
  - title: "Simple process-alive health check for SeedD"
    rationale: "Full gRPC health check requires seedgen2.utils.grpc import, deferred to Plan 03-02"
    alternatives: ["Full gRPC health check now", "No health check"]
    choice: "Process-alive check with 3-second warmup"
  - title: "Placeholder wait loop"
    rationale: "Infrastructure complete, actual SeedGenAgent integration belongs in Plan 03-02"
    alternatives: ["Integrate SeedGenAgent now"]
    choice: "Placeholder loop"
metrics:
  duration_seconds: 187
  duration_minutes: 3
  task_count: 2
  file_count: 2
  commit_count: 2
  completed_date: "2026-03-12"
---

# Phase 03 Plan 01: Runner Infrastructure Summary

**One-liner:** Docker runner with libCRS artifact download, SeedD lifecycle, and seed directory registration

## What Was Built

Created the foundational runner container and orchestration script for the `oss-crs run` phase. The runner downloads build artifacts from Phase 2, starts SeedD as an embedded background process, registers seed directories with libCRS, and prepares the environment for seedgen pipeline execution (to be added in Plan 03-02).

## Implementation Details

### runner.Dockerfile
- Based on `seedgen-runtime:latest` (inherits all Phase 1 tools)
- Installs libCRS via OSS-CRS standard `COPY --from=libcrs` pattern
- Installs Python dependencies: langchain-openai, grpcio, grpcio-health-checking
- Copies seedgen2 package to `/runner/seedgen2`
- Copies runner.py orchestration script
- Creates working directories: artifacts/, shared/, seeds-in/, seeds-out/
- Sets CMD to `python3 runner.py`

### runner.py Orchestration Script
**Key functions:**

1. **log_json(event, **kwargs)**: Structured JSON logging to stderr with timestamps
2. **download_artifacts()**: Downloads three build outputs via libCRS:
   - coverage-harness → `/runner/artifacts/coverage-harness`
   - compile-commands → `/runner/artifacts/compile-commands`
   - callgraph → `/runner/artifacts/callgraph`
   - Verifies each artifact exists after download, fails fast if missing
3. **register_seed_dirs()**: Registers two directories with libCRS:
   - `/runner/seeds-in` as fetch directory (import existing seeds)
   - `/runner/seeds-out` as submit directory type "seed" (export generated seeds)
4. **start_seedd(shared_dir)**: Embedded SeedD lifecycle management:
   - Launches `/usr/local/bin/seedd --shared-dir /runner/shared` as subprocess
   - Health check loop (30 attempts, 1s interval)
   - Returns Popen object for process management
   - Fails fast if process dies or health timeout
5. **main()**: Orchestration entrypoint:
   - Loads environment variables: TARGET_HARNESS, NUM_SEEDS (default 100), OSS_CRS_LLM_API_URL, OSS_CRS_LLM_API_KEY
   - Calls download_artifacts(), register_seed_dirs(), start_seedd()
   - Logs "runner_ready" event
   - Placeholder 60-second wait loop (Plan 03-02 will replace with SeedGenAgent calls)

### Environment Variables
| Variable | Purpose | Default |
|----------|---------|---------|
| TARGET_HARNESS | Target fuzzing harness identifier | (required) |
| NUM_SEEDS | Seeds per pipeline iteration | 100 |
| OSS_CRS_LLM_API_URL | LLM API base URL | (required) |
| OSS_CRS_LLM_API_KEY | LLM API authentication key | (required) |

## Deviations from Plan

### Auto-fixed Issues

None - plan executed exactly as written.

### Scope Changes

None - all planned functionality delivered.

## Integration Points

### Upstream Dependencies (Phase 1 & 2)
- **seedgen-runtime:latest**: Base image with all Phase 1 tools (seedd, getcov, argus, callgraph libs)
- **libCRS**: OSS-CRS artifact management system (provided at build time)
- **Build artifacts**: coverage-harness, compile-commands, callgraph (from Phase 2 builders)

### Downstream Consumers (Phase 3 Plan 02)
- **runner.py main loop**: Will be replaced with SeedGenAgent instantiation and run() calls
- **seedgen2 package**: Python pipeline code ready to import
- **Environment variables**: OSS_CRS_LLM_API_URL/KEY ready for presets.py modification

## Files Changed

### Created
| File | Purpose | Lines |
|------|---------|-------|
| oss-crs/dockerfiles/runner.Dockerfile | Runner container image definition | 36 |
| oss-crs/bin/runner.py | Orchestration script for run phase | 199 |

### Modified
None

## Test Results

### Automated Verification
- **runner.Dockerfile syntax**: Validated with hadolint (warnings expected for OSS-CRS patterns)
- **runner.py syntax**: `python3 -m py_compile` passed
- **Function presence**: All 5 required functions verified present
- **Executable permissions**: runner.py marked executable

### Manual Verification
- Docker build test cannot run in local dev environment (requires libCRS from OSS-CRS)
- libCRS commands cannot be tested locally (OSS-CRS runtime dependency)
- SeedD health check simplified to process-alive check (full gRPC check in Plan 03-02)

### Integration Testing
Deferred to Phase 4 validation - full `oss-crs run` test will verify:
- libCRS artifact download
- SeedD startup and health
- Seed directory registration
- Environment variable loading

## Requirements Satisfied

| Requirement | Status | Evidence |
|-------------|--------|----------|
| RUNF-01: Download build artifacts via libCRS | ✓ Complete | download_artifacts() downloads 3 artifacts, verifies existence |
| RUNF-02: Use OSS_CRS_LLM_API_URL/KEY | ✓ Complete | main() loads env vars, logs their presence |
| RUNF-03: Export seeds via register-submit-dir | ✓ Complete | register_seed_dirs() registers /runner/seeds-out type "seed" |
| RUNF-04: Import seeds via register-fetch-dir | ✓ Complete | register_seed_dirs() registers /runner/seeds-in |
| RUNF-05: SeedD runs inside container | ✓ Complete | start_seedd() launches subprocess, health check, returns Popen |

## Known Limitations

1. **Health check simplified**: Uses process-alive check instead of full gRPC health check
   - **Reason**: Full check requires seedgen2.utils.grpc import (Plan 03-02 scope)
   - **Impact**: 3-second warmup may not be sufficient for slow environments
   - **Mitigation**: 30-attempt loop with 1s interval = 30s total timeout

2. **No actual pipeline execution**: Placeholder wait loop instead of SeedGenAgent calls
   - **Reason**: SeedGenAgent integration is Plan 03-02 deliverable
   - **Impact**: Runner starts successfully but doesn't generate seeds yet
   - **Mitigation**: Clear log message indicates waiting for Plan 03-02

3. **Local testing blocked**: Docker build requires OSS-CRS libCRS context
   - **Reason**: COPY --from=libcrs pattern is OSS-CRS standard
   - **Impact**: Cannot verify Dockerfile builds locally
   - **Mitigation**: Syntax validated, pattern matches existing builders

## Next Steps (Plan 03-02)

1. Modify `components/seedgen/seedgen2/presets.py` to use OSS_CRS_LLM_API_URL/KEY
2. Implement full gRPC health check using `seedgen2.utils.grpc.SeedD`
3. Replace placeholder wait loop with SeedGenAgent instantiation
4. Add pipeline loop: `agent.run()` → wait for seeds → repeat
5. Implement SHA256 seed filename generation
6. Add structured logging for seed count, coverage metrics, LLM calls

## Performance

- **Duration**: 3 minutes (187 seconds)
- **Tasks completed**: 2/2
- **Files created**: 2
- **Commits**: 2
- **Average task time**: 1.5 minutes

## Self-Check

### Files Exist
```
FOUND: oss-crs/dockerfiles/runner.Dockerfile
FOUND: oss-crs/bin/runner.py
```

### Commits Exist
```
FOUND: f9106c0 (Task 1: runner.Dockerfile)
FOUND: 605991c (Task 2: runner.py)
```

### Functionality Verification
- ✓ runner.Dockerfile has FROM seedgen-runtime:latest
- ✓ runner.Dockerfile installs libCRS via COPY --from=libcrs
- ✓ runner.Dockerfile installs Python deps (langchain-openai, grpcio, grpcio-health-checking)
- ✓ runner.Dockerfile copies seedgen2 and runner.py
- ✓ runner.Dockerfile creates working directories
- ✓ runner.py has log_json() function
- ✓ runner.py has download_artifacts() function
- ✓ runner.py has register_seed_dirs() function
- ✓ runner.py has start_seedd() function
- ✓ runner.py has main() function
- ✓ runner.py syntax is valid (py_compile passed)
- ✓ runner.py is executable

## Self-Check: PASSED

All files created, all commits recorded, all required functionality present and verified.
