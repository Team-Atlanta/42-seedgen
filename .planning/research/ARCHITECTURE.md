# Architecture Patterns: OSS-CRS Integration

**Domain:** OSS-CRS CRS Integration
**Researched:** 2026-03-12
**Confidence:** HIGH (based on official OSS-CRS documentation and reference implementations)

## Executive Summary

OSS-CRS integrations follow a three-phase lifecycle model (prepare/build-target/run) with strict component isolation. Based on analysis of three reference CRS implementations (crs-libfuzzer, atlantis-multilang, buttercup-bugfind) and the official OSS-CRS documentation, a clear architectural pattern emerges:

1. **Prepare Phase**: Build CRS-specific Docker images via `docker buildx bake`
2. **Build-Target Phase**: Multiple parallel builders compile the target with different instrumentation configurations, outputting artifacts via `libCRS submit-build-output`
3. **Run Phase**: Multiple cooperating containers communicate via shared filesystem and DNS, with artifact submission via `libCRS register-submit-dir`

The seedgen integration must adapt from a RabbitMQ/PostgreSQL microservices architecture to this three-phase containerized model.

## Recommended Architecture

```
OSS-CRS Seedgen Integration
===========================

PREPARE PHASE (docker buildx bake)
----------------------------------
Build CRS images containing:
  - ARGUS compiler wrapper
  - GetCov coverage tools
  - SeedD gRPC server
  - Seedgen Python runtime + dependencies

BUILD-TARGET PHASE (parallel builders)
--------------------------------------
  +------------------+     +------------------+     +------------------+
  |  asan-builder    |     | coverage-builder |     | compile-commands |
  |                  |     |                  |     |    -builder      |
  | SANITIZER=asan   |     | SANITIZER=cov    |     | Generate JSON    |
  | Standard build   |     | Source coverage  |     | compile_commands |
  |                  |     |                  |     |                  |
  | Output:          |     | Output:          |     | Output:          |
  |   task/          |     |   task-coverage/ |     |   compile_cmds/  |
  +--------+---------+     +--------+---------+     +--------+---------+
           |                        |                        |
           +------------------------+------------------------+
                                    |
                          libCRS submit-build-output
                                    |
                                    v
                          +------------------+
                          | OSS_CRS_BUILD_   |
                          | OUT_DIR (shared) |
                          +------------------+

RUN PHASE (cooperating containers)
----------------------------------
  +------------------+     +------------------+     +------------------+
  |      redis       |     |   orchestrator   |     |     seedgen      |
  |                  |     |                  |     |                  |
  | In-memory queue  |     | Reads build      |     | LLM-driven seed  |
  | Task dispatch    |     | outputs, creates |     | generation with  |
  |                  |     | harness tasks    |     | coverage feedback|
  |                  |     | in Redis         |     |                  |
  +--------+---------+     +--------+---------+     +--------+---------+
           ^                        |                        |
           |                        |                        |
           +------------------------+                        |
                      Task queue                             |
                                                             |
                                                             v
                                              +------------------+
                                              | libCRS register- |
                                              | submit-dir seed  |
                                              | /output/seeds    |
                                              +------------------+
                                                       |
                                                       v
                                              OSS_CRS_SUBMIT_DIR
```

### Component Boundaries

| Component | Phase | Responsibility | Communicates With |
|-----------|-------|----------------|-------------------|
| **asan-builder** | build-target | Compile target with ASan, create task structure | libCRS (output) |
| **coverage-builder** | build-target | Compile target with source coverage | libCRS (output) |
| **compile-commands-builder** | build-target | Generate compile_commands.json for static analysis | libCRS (output) |
| **redis** | run | In-memory task queue, replaces RabbitMQ | orchestrator, seedgen |
| **orchestrator** | run | Read build outputs, create task entries | redis, libCRS (download) |
| **seedgen** | run | LLM-driven seed generation with coverage feedback | redis, LLM API, libCRS (submit) |

### Data Flow

```
BUILD-TARGET DATA FLOW
======================

Target Source (OSS-Fuzz format)
         |
         v
    +---------+
    | compile |  (OSS-Fuzz compile script)
    +---------+
         |
         +---> /out/{harness}         (ASan binary)
         +---> /out/{harness}_cov     (Coverage binary)
         +---> compile_commands.json  (Build database)
         |
         v
    +------------------------+
    | libCRS submit-build-   |
    | output <src> <dst>     |
    +------------------------+
         |
         v
    OSS_CRS_BUILD_OUT_DIR/{dst}


RUN PHASE DATA FLOW
===================

    +------------------------+
    | libCRS download-build- |
    | output <src> <dst>     |
    +------------------------+
         |
         v
    /artifacts/task/         (Task root with task_meta.json)
    /artifacts/task-coverage/  (Coverage build)
    /artifacts/compile_cmds/   (compile_commands.json)
         |
         v
    +---------------+
    | orchestrator  |  Reads task_meta.json, enumerates harnesses
    +---------------+
         |
         v
    Redis (harness queue)
         |
         v
    +---------------+
    |   seedgen     |  Pops harness from queue
    +---------------+
         |
         +---> Glance stage (quick LLM analysis)
         +---> Filetype stage (determine input type)
         +---> Alignment stage (structure discovery)
         +---> Coverage stage (iterative refinement)
         |
         v
    /output/seeds/{harness}/seed_*.bin
         |
         v
    +------------------------+
    | libCRS register-submit |
    | -dir seed /output/seeds|
    +------------------------+
         |
         v
    OSS_CRS_SUBMIT_DIR/seeds/
```

## Patterns to Follow

### Pattern 1: Multi-Builder Build-Target Phase

**What:** Define multiple build steps in `target_build_phase`, each producing distinct outputs.

**When:** The CRS needs multiple build configurations (ASan, coverage, compile_commands).

**Example:**
```yaml
# crs.yaml
target_build_phase:
  - name: build
    dockerfile: oss-crs/dockerfiles/builder.Dockerfile
    outputs:
      - task
  - name: build-coverage
    dockerfile: oss-crs/dockerfiles/builder-coverage.Dockerfile
    outputs:
      - task-coverage
  - name: build-codequery
    dockerfile: oss-crs/dockerfiles/builder-codequery.Dockerfile
    depends_on:
      - build
    outputs:
      - cqdb
```

**Reference:** buttercup-bugfind/oss-crs/crs.yaml

### Pattern 2: Orchestrator-Worker Pattern

**What:** One container reads build outputs and populates a task queue; other containers consume tasks.

**When:** Multiple independent workers need to process the same target.

**Example:**
```python
# orchestrator.py
def main():
    redis = Redis.from_url(redis_url)
    task_meta = TaskMeta.load(task_dir)

    # Register build outputs
    build_map.add_build(fuzzer_build)

    # Create weighted harness entries
    for tgt in get_fuzz_targets(build_dir):
        harness = WeightedHarness(harness_name=os.path.basename(tgt))
        harness_weights.push_harness(harness)
```

**Reference:** buttercup-bugfind/oss-crs/orchestrator.py

### Pattern 3: Environment Variable Mapping

**What:** Map OSS-CRS environment variables to existing service configuration.

**When:** Adapting existing code that expects different env var names.

**Example:**
```bash
# Map OSS-CRS LLM environment variables to existing format
if [ -n "$OSS_CRS_LLM_API_URL" ]; then
    export BUTTERCUP_LITELLM_HOSTNAME="$OSS_CRS_LLM_API_URL"
fi
if [ -n "$OSS_CRS_LLM_API_KEY" ]; then
    export BUTTERCUP_LITELLM_KEY="$OSS_CRS_LLM_API_KEY"
fi
```

**Reference:** buttercup-bugfind/oss-crs/bin/buttercup_entrypoint

### Pattern 4: Service Domain Resolution

**What:** Use `libCRS get-service-domain` to discover container endpoints dynamically.

**When:** Containers need to communicate with other containers in the CRS.

**Example:**
```bash
REDIS_HOST=$(libCRS get-service-domain redis)
export REDIS_URL="redis://${REDIS_HOST}:6379"
```

**Reference:** buttercup-bugfind/oss-crs/bin/buttercup_entrypoint

### Pattern 5: RUN_TYPE Multiplexing

**What:** Use a single Docker image with an entrypoint that branches on RUN_TYPE.

**When:** Multiple run-phase modules share most dependencies.

**Example:**
```bash
case "$RUN_TYPE" in
    redis)
        exec redis-server
        ;;
    orchestrator)
        exec python /crs/orchestrator.py
        ;;
    seedgen)
        libCRS register-submit-dir seed "$CORPUS_DIR" &
        exec seed-gen server
        ;;
esac
```

**Reference:** buttercup-bugfind/oss-crs/bin/buttercup_entrypoint

## Anti-Patterns to Avoid

### Anti-Pattern 1: Direct Container Communication

**What:** Using hardcoded hostnames or IP addresses between containers.

**Why bad:** Breaks portability between local and cloud deployments.

**Instead:** Use `libCRS get-service-domain <service_name>` for DNS-based discovery.

### Anti-Pattern 2: Persistent State in Containers

**What:** Relying on container filesystem for persistent state across restarts.

**Why bad:** Containers are ephemeral; state is lost on restart.

**Instead:** Use Redis for transient state, submit artifacts via libCRS for persistence.

### Anti-Pattern 3: Blocking Build Output Wait

**What:** Having run-phase containers block indefinitely waiting for build outputs.

**Why bad:** OSS-CRS runs build-target before run; outputs should already exist.

**Instead:** Use `depends_on` in crs.yaml for build ordering; fail fast if outputs missing.

### Anti-Pattern 4: External Network Dependencies in Build

**What:** Reaching out to external services (LLM APIs, package repos) during build-target phase.

**Why bad:** Build-target should be reproducible and fast; network calls add latency and failure modes.

**Instead:** Package all dependencies in prepare phase; defer LLM calls to run phase.

## Component Dependencies (Build Order)

```
PREPARE PHASE DEPENDENCIES
==========================

base-image
    |
    +---> seedgen-builder (Python deps)
    |           |
    +---> tool-builder (ARGUS, GetCov, SeedD)
                |
                v
           runtime (final image)


BUILD-TARGET PHASE DEPENDENCIES
===============================

target_base_image (from OSS-Fuzz)
    |
    +---> asan-builder (no deps)
    |
    +---> coverage-builder (no deps)
    |
    +---> compile-commands-builder (no deps)
    |
    +---> codequery-builder (depends_on: asan-builder)
                              ^
                              |
                Uses task/src from asan-builder


RUN PHASE DEPENDENCIES
======================

redis (no deps)
    ^
    |
orchestrator (depends: redis, build outputs)
    ^
    |
seedgen (depends: redis, orchestrator tasks, coverage build)
```

### Suggested Build Order for Implementation

1. **Prepare Phase Infrastructure**
   - Dockerfile for base image with uv, rsync, libCRS
   - docker-bake.hcl for image builds
   - Build stages for seedgen dependencies

2. **Builder Dockerfiles**
   - builder.Dockerfile (ASan build)
   - builder-coverage.Dockerfile (coverage build)
   - builder-compile-commands.Dockerfile (compile_commands.json generation)

3. **Builder Scripts**
   - builder-default.sh (standard ASan build with task structure)
   - builder-coverage.sh (coverage instrumented build)
   - builder-compile-commands.sh (JSON compilation database)

4. **Run Phase Infrastructure**
   - Combined runner Dockerfile (redis + orchestrator + seedgen)
   - Entrypoint script with RUN_TYPE routing

5. **Seedgen Adaptation**
   - Remove RabbitMQ dependencies
   - Remove PostgreSQL dependencies
   - Adapt to Redis-based task queue
   - Connect to OSS_CRS_LLM_API_URL for LLM calls
   - Submit seeds via libCRS

6. **crs.yaml Configuration**
   - Define all build phases and outputs
   - Define all run phase modules
   - Declare required_llms

## Key Environment Variables

| Variable | Phase | Purpose |
|----------|-------|---------|
| `OSS_CRS_NAME` | all | CRS name for DNS resolution |
| `OSS_CRS_TARGET` | all | Target project name |
| `OSS_CRS_TARGET_HARNESS` | all | Specific harness to target |
| `OSS_CRS_BUILD_OUT_DIR` | build/run | Shared build output directory |
| `OSS_CRS_SUBMIT_DIR` | run | Artifact submission directory |
| `OSS_CRS_SHARED_DIR` | run | Inter-container shared filesystem |
| `OSS_CRS_FETCH_DIR` | run | Read-only inter-CRS data exchange |
| `OSS_CRS_LLM_API_URL` | run | LiteLLM proxy endpoint |
| `OSS_CRS_LLM_API_KEY` | run | Per-CRS LLM API key |
| `FUZZING_LANGUAGE` | all | Target language (c, c++) |
| `SANITIZER` | build | Build sanitizer (address, coverage) |

## Recommended crs.yaml Structure

```yaml
name: seedgen
type:
  - bug-finding
version: "1.0.0"
docker_registry: ghcr.io/{org}/seedgen

prepare_phase:
  hcl: oss-crs/docker-bake.hcl

target_build_phase:
  - name: build
    dockerfile: oss-crs/dockerfiles/builder.Dockerfile
    outputs:
      - task
  - name: build-coverage
    dockerfile: oss-crs/dockerfiles/builder-coverage.Dockerfile
    outputs:
      - task-coverage
  - name: build-compile-commands
    dockerfile: oss-crs/dockerfiles/builder-compile-commands.Dockerfile
    outputs:
      - compile_commands

crs_run_phase:
  redis:
    dockerfile: oss-crs/dockerfiles/runner.Dockerfile
    additional_env:
      RUN_TYPE: redis
  orchestrator:
    dockerfile: oss-crs/dockerfiles/runner.Dockerfile
    additional_env:
      RUN_TYPE: orchestrator
  seedgen:
    dockerfile: oss-crs/dockerfiles/runner.Dockerfile
    additional_env:
      RUN_TYPE: seedgen

supported_target:
  mode:
    - full
    - delta
  language:
    - c
    - c++
  sanitizer:
    - address
  architecture:
    - x86_64

required_llms:
  - o3-mini
  - claude-sonnet-4-5-20250929
  - gpt-4o
```

## Sources

- OSS-CRS Development Guide: `/home/andrew/post/oss-crs-6/docs/crs-development-guide.md`
- OSS-CRS Architecture: `/home/andrew/post/oss-crs-6/docs/design/architecture.md`
- libCRS Reference: `/home/andrew/post/oss-crs-6/docs/design/libCRS.md`
- crs-libfuzzer (simple reference): `/home/andrew/post/crs-libfuzzer/oss-crs/crs.yaml`
- atlantis-multilang (complex reference): `/home/andrew/post/atlantis-multilang-wo-concolic/oss-crs/crs.yaml`
- buttercup-bugfind (seedgen reference): `/home/andrew/post/buttercup-bugfind/oss-crs/crs.yaml`

---

*Architecture research: 2026-03-12*
