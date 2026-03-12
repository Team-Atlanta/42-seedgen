# Phase 3: Run - Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Execute `oss-crs run` with the seedgen pipeline to generate fuzzing seeds. Runner downloads build artifacts, runs SeedD for coverage collection, orchestrates seedgen2 pipeline, and submits seeds via libCRS. Success: seeds appear in submission directory.

</domain>

<decisions>
## Implementation Decisions

### Runner Architecture
- SeedD runs embedded as background process inside runner container (not sidecar)
- Python script (runner.py) as entrypoint orchestrates: download artifacts, start SeedD, run seedgen, submit seeds
- Import and call SeedGenAgent from seedgen2 directly — minimal changes to existing code
- Target-specific harness via --target-harness flag or TARGET_HARNESS env var

### Container Lifecycle
- Long-lived container — does NOT restart between runs
- Runner.py loops externally: call SeedGenAgent.run() repeatedly with fresh state
- No delay between pipeline runs — maximum throughput
- Container stays alive until system stops it

### Seed Output Strategy
- NUM_SEEDS env var configures seeds per pipeline iteration (default 100)
- Incremental submission — seeds submitted as they're generated, not batched at end
- No deduplication in runner — downstream libfuzzer handles that
- Seed filenames are SHA256 content hashes for automatic dedup on disk
- Use libCRS register-submit-dir for output — standard OSS-CRS pattern

### Seed Input
- Always use libCRS register-fetch-dir to import existing seeds (not optional)
- Seeds from previous runs or other sources are available to seedgen pipeline

### Logging
- Structured JSON logs for seed count, coverage metrics, LLM calls
- Easy to parse, matches OSS-CRS patterns

### Claude's Discretion
- LLM configuration (model selection, timeouts, retries)
- Exact SeedD startup sequence and health checking
- Error handling and recovery strategies
- Directory structure inside runner container

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `components/seedgen/seedgen2/seedgen.py`: SeedGenAgent class with run() method
- `components/seedgen/seedgen2/utils/grpc.py`: SeedD gRPC client wrapper
- `components/seedgen/seedd/`: SeedD gRPC server binary (Go)
- `seedgen-runtime:latest`: Prepare-phase image with all tools

### Established Patterns
- SeedGenAgent takes: result_dir, ip_addr, project_name, harness_binary, gen_model
- SeedD initialized with ip_addr and shared_dir
- Stages: glance → filetype → alignment → coverage
- Each stage generates and evaluates seeds progressively
- libCRS submit-build-output / download-build-output for artifacts

### Integration Points
- Download coverage-harness, compile-commands, callgraph from build-target phase
- LLM access via OSS_CRS_LLM_API_URL and OSS_CRS_LLM_API_KEY
- Seed export via libCRS register-submit-dir seed

</code_context>

<specifics>
## Specific Ideas

- Follow existing seedgen2 orchestration pattern — don't reinvent
- Modify presets.py to use OSS_CRS_LLM_API_URL instead of custom LiteLLM
- Wrap existing task_handler.py pattern but remove RabbitMQ dependency

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-run*
*Context gathered: 2026-03-12*
