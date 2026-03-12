# Phase 3: Run - Research

**Researched:** 2026-03-12
**Domain:** Python runner orchestration, SeedD gRPC integration, libCRS artifact management
**Confidence:** HIGH

## Summary

Phase 3 implements the `oss-crs run` command by creating a Python runner that orchestrates the existing seedgen2 pipeline. The runner downloads build artifacts from Phase 2, starts SeedD as an embedded background process, calls SeedGenAgent.run() in a loop, and exports seeds via libCRS.

The existing codebase provides well-structured components that can be directly reused: SeedGenAgent (seedgen.py), SeedD gRPC wrapper (utils/grpc.py), and the multi-stage pipeline (glance/filetype/alignment/coverage agents). The main adaptation is replacing RabbitMQ/PostgreSQL dependencies with direct orchestration and libCRS integration.

**Primary recommendation:** Create a minimal runner.py that wraps existing SeedGenAgent with libCRS artifact download/upload, modify presets.py to use OSS_CRS_LLM_API_URL, and embed SeedD startup in the runner lifecycle.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- SeedD runs embedded as background process inside runner container (not sidecar)
- Python script (runner.py) as entrypoint orchestrates: download artifacts, start SeedD, run seedgen, submit seeds
- Import and call SeedGenAgent from seedgen2 directly — minimal changes to existing code
- Target-specific harness via --target-harness flag or TARGET_HARNESS env var
- Long-lived container — does NOT restart between runs
- Runner.py loops externally: call SeedGenAgent.run() repeatedly with fresh state
- No delay between pipeline runs — maximum throughput
- Container stays alive until system stops it
- NUM_SEEDS env var configures seeds per pipeline iteration (default 100)
- Incremental submission — seeds submitted as they're generated, not batched at end
- No deduplication in runner — downstream libfuzzer handles that
- Seed filenames are SHA256 content hashes for automatic dedup on disk
- Use libCRS register-submit-dir for output — standard OSS-CRS pattern
- Always use libCRS register-fetch-dir to import existing seeds (not optional)
- Structured JSON logs for seed count, coverage metrics, LLM calls

### Claude's Discretion
- LLM configuration (model selection, timeouts, retries)
- Exact SeedD startup sequence and health checking
- Error handling and recovery strategies
- Directory structure inside runner container

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RUNF-01 | Runner downloads build artifacts via libCRS download-build-output | Use `libcrs download-build-output` for coverage-harness, compile-commands, callgraph |
| RUNF-02 | Runner uses OSS_CRS_LLM_API_URL and OSS_CRS_LLM_API_KEY for LLM access | Modify presets.py to use these env vars instead of LITELLM_BASE_URL/LITELLM_KEY |
| RUNF-03 | Runner exports seeds via libCRS register-submit-dir seed | Register output directory with libCRS, write seeds with SHA256 filenames |
| RUNF-04 | Runner imports seeds via libCRS register-fetch-dir | Always register fetch directory for existing seeds from previous runs |
| RUNF-05 | SeedD gRPC service runs inside container for coverage collection | Start SeedD binary as subprocess, wait for health check before pipeline |
| SEED-01 | Glance stage generates initial Python generator script from harness | Existing generate_first_script() in agents/glance.py |
| SEED-02 | Filetype stage detects file format and enhances generator | Existing get_filetype() and generate_based_on_filetype() in agents/filetype.py |
| SEED-03 | Alignment stage documents structure requirements and aligns script | Existing align_script() and update_doc() in agents/alignment.py |
| SEED-04 | Coverage stage iteratively improves script based on coverage feedback | Existing generate_based_on_coverage() in agents/coverage.py |
| SEED-05 | Multi-model LLM orchestration (o3-mini, claude-3.5-sonnet, gpt-4o) | Existing presets.py model classes, adapt for OSS_CRS_LLM_API_URL |
| SEED-06 | Call graph extraction for function relationship analysis | Existing SeedD.get_call_graph() via utils/grpc.py |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| langchain-openai | existing | LLM API client via ChatOpenAI | Already used in presets.py, OpenAI-compatible with any base_url |
| grpcio | existing | SeedD gRPC communication | Already used in utils/grpc.py |
| grpcio-health-checking | existing | SeedD health checks | Already used for service readiness |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| subprocess | stdlib | Start SeedD as background process | Runner startup |
| hashlib | stdlib | SHA256 seed filenames | Seed deduplication on disk |
| json | stdlib | Structured logging output | All runner logging |

### libCRS Commands
| Command | Purpose | When to Use |
|---------|---------|-------------|
| `libcrs download-build-output <name>` | Download build artifacts | Runner startup |
| `libcrs register-submit-dir seed <path>` | Register seed output directory | Before pipeline starts |
| `libcrs register-fetch-dir <path>` | Register seed input directory | Before pipeline starts |

## Architecture Patterns

### Recommended Directory Structure
```
/runner/
├── runner.py           # Main entrypoint script
├── seedgen2/           # Copy of existing seedgen2 package
│   ├── agents/         # glance, filetype, alignment, coverage
│   ├── utils/          # grpc, seeds, coverage, etc.
│   └── presets.py      # Modified for OSS_CRS_LLM_API_URL
├── artifacts/          # Downloaded build outputs
│   ├── coverage-harness/
│   ├── compile-commands/
│   └── callgraph/
├── shared/             # SeedD shared directory
├── seeds-in/           # libCRS register-fetch-dir target
└── seeds-out/          # libCRS register-submit-dir target
```

### Pattern 1: Embedded SeedD Lifecycle
**What:** Start SeedD as subprocess, health check, run pipeline, keep alive
**When to use:** Runner startup
**Example:**
```python
import subprocess
import time
from seedgen2.utils.grpc import SeedD

def start_seedd(shared_dir: str) -> subprocess.Popen:
    proc = subprocess.Popen(
        ["/usr/local/bin/seedd", "--shared-dir", shared_dir],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    # Wait for health check
    seedd = SeedD("localhost", shared_dir)
    for _ in range(30):
        try:
            seedd.health_check()
            return proc
        except:
            time.sleep(1)
    raise RuntimeError("SeedD failed to start")
```

### Pattern 2: Continuous Pipeline Loop
**What:** Call SeedGenAgent.run() repeatedly without container restart
**When to use:** Main runner loop
**Example:**
```python
while True:
    agent = SeedGenAgent(
        result_dir=result_dir,
        ip_addr="localhost",
        project_name=project_name,
        harness_binary=harness_path,
        gen_model=gen_model
    )
    agent.run()
    # Seeds written to result_dir, libCRS picks them up
```

### Pattern 3: SHA256 Seed Filenames
**What:** Name seeds by content hash for automatic deduplication
**When to use:** Seed output
**Example:**
```python
import hashlib

def write_seed(seed_data: bytes, output_dir: str) -> str:
    sha256 = hashlib.sha256(seed_data).hexdigest()
    path = os.path.join(output_dir, sha256)
    with open(path, 'wb') as f:
        f.write(seed_data)
    return path
```

### Anti-Patterns to Avoid
- **Batched seed submission:** Submit incrementally, not at end
- **Custom deduplication:** Let downstream handle it, use SHA256 filenames
- **Container restart per run:** Keep container alive, loop internally

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM API client | Custom HTTP client | langchain-openai ChatOpenAI | Already integrated, handles retries |
| Coverage collection | Custom instrumentation | SeedD + GetCov via gRPC | Battle-tested, already built |
| Artifact transfer | Custom file sync | libCRS download-build-output | OSS-CRS standard pattern |
| Seed export | Custom upload logic | libCRS register-submit-dir | OSS-CRS standard pattern |

## Common Pitfalls

### Pitfall 1: SeedD Not Ready
**What goes wrong:** Pipeline starts before SeedD gRPC server is listening
**Why it happens:** SeedD binary takes time to initialize
**How to avoid:** Health check loop with timeout before starting pipeline
**Warning signs:** gRPC UNAVAILABLE errors early in execution

### Pitfall 2: Wrong LLM Environment Variables
**What goes wrong:** presets.py looks for LITELLM_BASE_URL, OSS-CRS provides OSS_CRS_LLM_API_URL
**Why it happens:** Original code designed for different infrastructure
**How to avoid:** Modify presets.py to use OSS_CRS_LLM_API_URL and OSS_CRS_LLM_API_KEY
**Warning signs:** LLM calls fail with connection errors

### Pitfall 3: SeedD Shared Directory Mismatch
**What goes wrong:** SeedD can't find files written by Python
**Why it happens:** SeedD and Python have different shared_dir paths
**How to avoid:** Use consistent absolute path for shared directory
**Warning signs:** FileNotFoundError in SeedD operations

### Pitfall 4: Missing Build Artifacts
**What goes wrong:** Harness binary or compile_commands.json not found
**Why it happens:** libCRS download not complete or paths wrong
**How to avoid:** Verify all artifacts exist after download, fail fast
**Warning signs:** FileNotFoundError early in pipeline

## Code Examples

### presets.py Modification
```python
# Change from:
base_url=os.getenv("LITELLM_BASE_URL")
api_key=SecretStr(os.getenv("LITELLM_KEY"))

# To:
base_url=os.getenv("OSS_CRS_LLM_API_URL")
api_key=SecretStr(os.getenv("OSS_CRS_LLM_API_KEY"))
```

### Structured JSON Logging
```python
import json
import sys

def log_json(event: str, **kwargs):
    entry = {"event": event, **kwargs}
    print(json.dumps(entry), file=sys.stderr, flush=True)

# Usage:
log_json("seed_generated", count=10, coverage=0.42)
log_json("pipeline_complete", iteration=1, total_seeds=100)
```

### Runner Entrypoint
```python
#!/usr/bin/env python3
import os
import subprocess

# Download artifacts
subprocess.run(["libcrs", "download-build-output", "coverage-harness"], check=True)
subprocess.run(["libcrs", "download-build-output", "compile-commands"], check=True)
subprocess.run(["libcrs", "download-build-output", "callgraph"], check=True)

# Register seed directories
subprocess.run(["libcrs", "register-fetch-dir", "/runner/seeds-in"], check=True)
subprocess.run(["libcrs", "register-submit-dir", "seed", "/runner/seeds-out"], check=True)

# Start SeedD and run pipeline loop
# ...
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing in seedgen2) |
| Config file | components/seedgen/seedgen2/conftest.py |
| Quick run command | `pytest components/seedgen/seedgen2/ -x -q` |
| Full suite command | `pytest components/seedgen/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RUNF-01 | Artifact download | integration | Manual - requires libCRS | N/A |
| RUNF-02 | LLM API access | integration | Manual - requires API | N/A |
| RUNF-03 | Seed export | integration | Manual - requires libCRS | N/A |
| RUNF-04 | Seed import | integration | Manual - requires libCRS | N/A |
| RUNF-05 | SeedD startup | integration | Manual - requires binary | N/A |
| SEED-01 | Glance stage | unit | `pytest seedgen2/agents/glance.py -x` | Check existing |
| SEED-02 | Filetype stage | unit | `pytest seedgen2/agents/filetype.py -x` | Check existing |
| SEED-03 | Alignment stage | unit | `pytest seedgen2/agents/alignment.py -x` | Check existing |
| SEED-04 | Coverage stage | unit | `pytest seedgen2/agents/coverage.py -x` | Check existing |
| SEED-05 | Multi-model LLM | integration | Manual - requires API | N/A |
| SEED-06 | Call graph | unit | Covered by SeedD tests | Check existing |

### Sampling Rate
- **Per task commit:** Run linting only (no external dependencies)
- **Per wave merge:** Manual integration test with local SeedD
- **Phase gate:** Full pipeline test via `oss-crs run` in Phase 4

### Wave 0 Gaps
- [ ] Runner.py does not exist yet - needs creation
- [ ] presets.py modification for OSS_CRS_LLM_API_URL
- [ ] Dockerfile.runner for run phase container

## Sources

### Primary (HIGH confidence)
- Existing codebase: components/seedgen/seedgen2/seedgen.py - SeedGenAgent class
- Existing codebase: components/seedgen/seedgen2/presets.py - LLM configuration
- Existing codebase: components/seedgen/seedgen2/utils/grpc.py - SeedD wrapper
- Existing codebase: components/seedgen/task_handler.py - Orchestration patterns

### Secondary (MEDIUM confidence)
- CONTEXT.md: User decisions from discussion phase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - using existing libraries from codebase
- Architecture: HIGH - following established patterns from task_handler.py
- Pitfalls: HIGH - derived from code analysis of existing integration

**Research date:** 2026-03-12
**Valid until:** 2026-04-12 (stable codebase, no external dependencies changing)
