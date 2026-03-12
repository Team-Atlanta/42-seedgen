# Domain Pitfalls: OSS-CRS Integration

**Domain:** CRS integration for seedgen into OSS-CRS framework
**Researched:** 2026-03-12
**Confidence:** HIGH (based on reference CRS implementations: crs-libfuzzer, atlantis-multilang, buttercup-bugfind)

---

## Critical Pitfalls

Mistakes that cause rewrites, CI failures, or fundamental integration breakage.

### Pitfall 1: Incorrect Build Output Path Registration

**What goes wrong:** Build outputs submitted via `libCRS submit-build-output` do not match the `outputs` list in `crs.yaml`, causing OSS-CRS validation to fail or run phase to crash when `download-build-output` cannot find expected artifacts.

**Why it happens:**
- `crs.yaml` declares `outputs: [foo/build, foo/src]` but compile script calls `libCRS submit-build-output $OUT build` (missing the `foo/` prefix)
- Developer tests locally without full OSS-CRS validation
- Copy-pasted patterns from simpler CRS without adapting paths

**Consequences:**
- `oss-crs build-target` completes but outputs missing
- Run phase containers fail immediately with "build output not found"
- Confusing errors because the build "succeeded"

**Prevention:**
1. Match `crs.yaml` outputs exactly with `submit-build-output` dst_path arguments
2. Add validation script that parses crs.yaml and verifies all outputs are submitted or skipped
3. Test with `oss-crs build-target` before integrating run phase

**Detection (warning signs):**
- Build phase exits 0 but run phase immediately fails
- Error messages mentioning "rsync: change_dir" or "No such file or directory" for build paths
- `libCRS download-build-output` returning non-zero exit code

**Phase mapping:** Build-target phase implementation

---

### Pitfall 2: Missing libCRS Installation in Dockerfiles

**What goes wrong:** Containers fail at runtime because `libCRS` command is not found. Build-target or run-phase scripts cannot submit outputs, download artifacts, or register directories.

**Why it happens:**
- Developer forgets to add libCRS installation block to Dockerfile
- Installation block is present but uses wrong path (`/libCRS` vs `/opt/libCRS`)
- Multi-stage Docker build loses libCRS between stages

**Consequences:**
- Build phase cannot submit outputs, target remains unbuilt
- Run phase cannot download build outputs, CRS never starts
- Error: "libCRS: command not found"

**Prevention:**
```dockerfile
# Standard libCRS installation pattern - add to EVERY builder and runner Dockerfile
COPY --from=libcrs . /opt/libCRS
RUN /opt/libCRS/install.sh
```

**Detection:**
- "command not found: libCRS" in container logs
- Scripts failing on first libCRS invocation
- Build/run containers exiting immediately with error

**Phase mapping:** Prepare phase (Dockerfile authoring), verified in build-target and run phases

---

### Pitfall 3: Environment Variable Mapping Mismatch for LLM Access

**What goes wrong:** LLM calls fail because the CRS code expects different environment variable names than OSS-CRS provides. Seeds are not generated, or generation crashes.

**Why it happens:**
- Existing seedgen uses custom env vars (e.g., `LITELLM_URL`, `LITELLM_KEY`, `OPENAI_API_KEY`)
- OSS-CRS provides `OSS_CRS_LLM_API_URL` and `OSS_CRS_LLM_API_KEY`
- Developer ports code but doesn't update environment variable references

**Consequences:**
- LLM client initialization fails (empty base_url or api_key)
- Silent failures if code defaults to empty strings
- Seeds not generated, no errors in OSS-CRS logs (LLM errors in container logs)

**Prevention:**
1. Create explicit mapping in entrypoint script (pattern from atlantis-multilang):
```bash
export LITELLM_URL=$OSS_CRS_LLM_API_URL
export LITELLM_KEY=$OSS_CRS_LLM_API_KEY
```
2. Or update Python code to read OSS-CRS variables directly:
```python
base_url = os.environ.get("OSS_CRS_LLM_API_URL")
api_key = os.environ.get("OSS_CRS_LLM_API_KEY")
```

**Detection:**
- LLM client throws connection errors or authentication failures
- Empty `base_url` in OpenAI client initialization
- Seeds not appearing despite no build/run errors

**Phase mapping:** Run phase implementation

---

### Pitfall 4: Blocking on Missing Redis/PostgreSQL Infrastructure

**What goes wrong:** Ported code still tries to connect to RabbitMQ/PostgreSQL that don't exist in OSS-CRS. Container hangs waiting for connection or crashes immediately.

**Why it happens:**
- Existing seedgen deeply integrated with message queue task distribution
- Database session initialization code runs at import time
- Hardcoded connection strings or default fallbacks pointing to non-existent hosts

**Consequences:**
- Container hangs indefinitely on startup (waiting for RabbitMQ)
- Import-time crashes with connection refused errors
- Non-obvious failures if code has aggressive retry loops

**Prevention:**
1. Audit all infrastructure dependencies before porting:
   - `utils/redis.py` - Keep (OSS-CRS CRSs can run Redis internally like buttercup)
   - `utils/db.py` - Remove or stub (no PostgreSQL in OSS-CRS)
   - `task_handler.py` RabbitMQ consumer - Replace with direct orchestration
2. Use feature flags or environment checks:
```python
if os.environ.get("OSS_CRS_NAME"):
    # OSS-CRS mode: skip queue initialization
    pass
else:
    # Legacy mode: connect to RabbitMQ
    connect_to_rabbitmq()
```

**Detection:**
- Container startup hangs (check `docker logs`)
- Connection refused errors in early log output
- "AMQP connection failed" or "PostgreSQL connection refused" messages

**Phase mapping:** Initial porting work, before any OSS-CRS testing

---

### Pitfall 5: Seed Submission Directory Not Registered

**What goes wrong:** Seeds are generated but never appear in OSS-CRS artifacts. The CRS runs without errors but produces no visible output.

**Why it happens:**
- Existing seedgen writes seeds to database or message queue, not filesystem
- Developer assumes OSS-CRS automatically collects files from some directory
- `libCRS register-submit-dir` called but with wrong path or not backgrounded

**Consequences:**
- Seeds exist in container filesystem but are not submitted to OSS-CRS
- `oss-crs artifacts` shows empty seed list
- Appears as if seedgen is not working, but it actually is

**Prevention:**
1. Register submit directory in entrypoint, with background execution:
```bash
libCRS register-submit-dir seed /output/seeds &
```
2. Ensure seedgen code writes to the registered directory
3. Verify with `ls -la` in container that seeds appear where expected

**Detection:**
- Seeds not appearing in `oss-crs artifacts` output
- Manual `docker exec` shows seeds exist in container but not in SUBMIT_DIR
- No `libCRS` process visible in container process list

**Phase mapping:** Run phase implementation

---

### Pitfall 6: Docker Build Context Missing Required Files

**What goes wrong:** Docker build fails because files referenced in COPY commands are outside the build context, or HCL file references files that don't exist relative to context root.

**Why it happens:**
- CRS repository structure differs from what Dockerfile expects
- HCL file sets context to subdirectory but COPY uses paths relative to repo root
- External dependencies (ARGUS, GetCov, SeedD source) not included in repo

**Consequences:**
- `oss-crs prepare` fails with "COPY failed: file not found"
- Prepare phase never completes, cannot proceed to build-target
- Confusing because local `docker build` might work with different context

**Prevention:**
1. Structure repository so all COPY sources are under `oss-crs/` or explicitly included context
2. Test with OSS-CRS prepare command, not just local docker build
3. For external dependencies like ARGUS/GetCov, either:
   - Vendor into repo
   - Build in multi-stage Dockerfile from source URLs
   - Use git submodules (but test that HCL handles them correctly)

**Detection:**
- "COPY failed" errors during prepare phase
- Files exist in repo but Docker cannot find them
- HCL context path vs COPY path mismatch

**Phase mapping:** Prepare phase implementation

---

## Moderate Pitfalls

### Pitfall 7: Multiple Build Phases Without Dependency Management

**What goes wrong:** Build phases run in parallel but one depends on artifacts from another. Race condition causes intermittent build failures.

**Why it happens:**
- Developer declares multiple `target_build_phase` entries (coverage, compile_commands, callgraph)
- Doesn't specify `depends_on` when one build needs output from another
- Works locally due to timing luck, fails in OSS-CRS parallel execution

**Consequences:**
- Build failures that are hard to reproduce locally
- "File not found" for outputs from parallel build
- Intermittent success/failure pattern

**Prevention:**
1. Use `depends_on` in crs.yaml when build steps have dependencies:
```yaml
target_build_phase:
  - name: build
    dockerfile: oss-crs/dockerfiles/builder.Dockerfile
    outputs:
      - build
  - name: build-codequery
    dockerfile: oss-crs/dockerfiles/builder-codequery.Dockerfile
    depends_on:
      - build
    outputs:
      - cqdb
```
2. Design builds to be independent where possible

**Detection:**
- Build failures that don't reproduce locally
- "No such file" errors for outputs from other build phases
- Success depends on which build finishes first

**Phase mapping:** Build-target phase design

---

### Pitfall 8: gRPC Service (SeedD) Port Conflicts or Network Issues

**What goes wrong:** SeedD gRPC server starts but cannot communicate with seedgen client. Coverage feedback loop broken, seeds generated without coverage guidance.

**Why it happens:**
- gRPC server binds to localhost but client is in different container
- Port hardcoded but conflicts with other services
- Docker network isolation prevents container-to-container communication

**Consequences:**
- Seedgen runs but coverage-guided iteration doesn't work
- Seeds generated are lower quality (no coverage feedback)
- Silent degradation - no errors, just worse results

**Prevention:**
1. Use `libCRS get-service-domain` for service discovery:
```bash
SEEDD_HOST=$(libCRS get-service-domain seedd)
export SEEDD_URL="http://${SEEDD_HOST}:50051"
```
2. Bind gRPC server to 0.0.0.0, not 127.0.0.1
3. Define SeedD as separate module in `crs_run_phase` if it runs as persistent service

**Detection:**
- gRPC "connection refused" or "name resolution failed" errors
- Coverage values always 0 or never updating
- Seedgen logs showing "skipping coverage" or similar fallback

**Phase mapping:** Run phase architecture design

---

### Pitfall 9: ARGUS/GetCov Build Failures from Source

**What goes wrong:** ARGUS LLVM wrapper or GetCov instrumentation fails to compile from source during prepare phase. Multi-hour build failures.

**Why it happens:**
- LLVM version mismatch with target project base image
- Missing build dependencies (cmake, ninja, LLVM development headers)
- Source URL changes or repo becomes unavailable

**Consequences:**
- Prepare phase takes hours then fails
- Cannot proceed to build-target or run phases
- Difficult to debug compiler errors in Docker build context

**Prevention:**
1. Pin exact LLVM version and commit hashes for reproducibility
2. Use multi-stage build: compile ARGUS/GetCov in separate stage, COPY binaries
3. Consider pre-building tooling images and referencing via archive pattern (like atlantis-multilang):
```dockerfile
FROM multilang-c-archive AS crs-tools-c
# ...
COPY --from=crs-tools-c /multilang-builder/llvm-patched /opt/llvm-patched
```

**Detection:**
- Prepare phase running for >30 minutes
- CMake or clang errors in build logs
- LLVM version conflict messages

**Phase mapping:** Prepare phase implementation

---

### Pitfall 10: Harness Name Mismatch Between Build and Run

**What goes wrong:** Build phase compiles harness with one name, run phase looks for different name. CRS cannot find the harness to run.

**Why it happens:**
- OSS-Fuzz project has multiple harnesses, name passed as `OSS_CRS_TARGET_HARNESS`
- Build phase ignores this and builds all harnesses
- Run phase looks for specific harness in wrong location

**Consequences:**
- Run phase immediately fails: "harness not found"
- Error message may not clearly indicate which harness was expected vs found
- Works for some harnesses, fails for others

**Prevention:**
1. Respect `OSS_CRS_TARGET_HARNESS` in both build and run phases
2. Verify harness exists at expected path in run phase startup:
```bash
HARNESS_PATH="/out/${OSS_CRS_TARGET_HARNESS}"
if [ ! -x "$HARNESS_PATH" ]; then
    echo "ERROR: Harness not found: $HARNESS_PATH"
    exit 1
fi
```
3. Log available harnesses on build completion for debugging

**Detection:**
- "harness not found" or "no such file" errors for executable
- Run phase checking wrong directory for harness
- Build logs showing harness compiled to different path

**Phase mapping:** Build-target and run phase coordination

---

## Minor Pitfalls

### Pitfall 11: Missing `set -e` in Shell Scripts

**What goes wrong:** Build or run script has an error but continues executing. Partial or corrupt artifacts are submitted.

**Prevention:**
```bash
#!/bin/bash
set -e  # Exit on first error
```

**Phase mapping:** All shell scripts

---

### Pitfall 12: Background Process Management in Entrypoint

**What goes wrong:** Background processes (register-submit-dir daemons) not properly managed. Container exits before seeds submitted, or processes become zombies.

**Prevention:**
1. Use `&` for background processes that should survive
2. Use `exec` for the final foreground process
3. Implement signal handling if graceful shutdown needed:
```bash
libCRS register-submit-dir seed /seeds &
SUBMIT_PID=$!
trap "kill $SUBMIT_PID 2>/dev/null" EXIT
exec main_process
```

**Phase mapping:** Run phase entrypoint scripts

---

### Pitfall 13: Assuming Build Outputs Are Tarballs

**What goes wrong:** Run phase expects tarball but build phase submitted directory. Or vice versa.

**Why it happens:** `libCRS submit-build-output` handles both files and directories transparently via rsync, but developer assumes specific format.

**Prevention:**
- Be consistent: always submit directories, always expect directories
- Document the format in comments
- Pattern from reference CRSs: submit directories, download to directories

**Phase mapping:** Build-target and run phase data flow

---

### Pitfall 14: Forgetting to Skip Optional Build Outputs

**What goes wrong:** Build step doesn't produce an optional output (e.g., coverage build for JVM), but doesn't call `libCRS skip-build-output`. Validation fails.

**Prevention:**
```bash
if [ "$BUILD_TYPE" = "coverage" ] && [ "$FUZZING_LANGUAGE" = "jvm" ]; then
    libCRS skip-build-output coverage/build
fi
```

**Detection:**
- OSS-CRS reports "missing build output" for optional step
- Build phase exits 0 but validation fails

**Phase mapping:** Build-target phase for edge cases

---

### Pitfall 15: Redis Timing Issues Between Services

**What goes wrong:** Services start in parallel but one depends on Redis being populated by another. Race condition causes early reads to fail.

**Why it happens:**
- Orchestrator populates Redis
- Seed-gen/coverage-bot read from Redis
- No synchronization mechanism

**Prevention (pattern from buttercup):**
1. Wait for Redis availability:
```bash
for i in $(seq 1 60); do
    if timeout 1 bash -c "echo > /dev/tcp/${REDIS_HOST}/6379" 2>/dev/null; then
        break
    fi
    sleep 1
done
```
2. Wait for orchestrator to finish (check for specific Redis keys)
3. Have services gracefully handle missing data with retry

**Phase mapping:** Run phase service coordination

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Prepare | Docker build context issues (#6) | Test with oss-crs prepare, not just docker build |
| Prepare | ARGUS/GetCov long builds (#9) | Use pre-built archives or multi-stage caching |
| Build-target | Output path mismatch (#1) | Match crs.yaml outputs exactly |
| Build-target | Missing libCRS (#2) | Standard installation block in all Dockerfiles |
| Build-target | Parallel build dependencies (#7) | Use depends_on for sequential builds |
| Run | LLM env var mismatch (#3) | Explicit mapping in entrypoint |
| Run | Infrastructure dependencies (#4) | Audit and remove RabbitMQ/PostgreSQL deps |
| Run | Seeds not submitted (#5) | Background register-submit-dir |
| Run | gRPC networking (#8) | Use get-service-domain, bind 0.0.0.0 |
| Run | Service timing (#15) | Add Redis availability checks |

---

## Sources

- `/home/andrew/post/oss-crs-6/docs/crs-development-guide.md` (OSS-CRS official development guide)
- `/home/andrew/post/oss-crs-6/docs/design/libCRS.md` (libCRS API reference)
- `/home/andrew/post/crs-libfuzzer/` (Simple reference CRS implementation)
- `/home/andrew/post/atlantis-multilang-wo-concolic/` (Complex multi-module CRS with LLM)
- `/home/andrew/post/buttercup-bugfind/` (Seed generation CRS with Redis coordination)
- `/home/andrew/post/42-seedgen/.planning/codebase/CONCERNS.md` (Existing seedgen known issues)
