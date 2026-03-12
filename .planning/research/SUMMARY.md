# Project Research Summary

**Project:** 42-seedgen OSS-CRS Integration
**Domain:** CRS Integration for LLM-Powered Seed Generation System
**Researched:** 2026-03-12
**Confidence:** HIGH

## Executive Summary

The 42-seedgen project requires integrating an existing LLM-powered seed generation pipeline into OSS-CRS's three-phase architecture (prepare/build-target/run). This integration involves replacing the current RabbitMQ/PostgreSQL microservices architecture with OSS-CRS's containerized, filesystem-based orchestration model while preserving the core seedgen functionality.

The recommended approach follows patterns from reference CRSs (particularly buttercup-bugfind, which has similar seed generation requirements). The integration centers on: (1) adapting the existing Python seedgen pipeline to use OSS-CRS's LLM proxy and artifact management, (2) containerizing the build process to produce both ASan and coverage-instrumented binaries, (3) replacing message queue task distribution with a Redis-based orchestrator pattern. The existing components (ARGUS, GetCov, SeedD) are preserved but repackaged into OSS-CRS's Dockerfile/HCL structure.

Key risks include the complexity of multi-instrumentation builds (ASan + coverage + compile_commands), potential LLVM version conflicts in ARGUS/GetCov compilation, and the critical importance of exact path matching between crs.yaml declarations and libCRS API calls. These risks are mitigated through strict adherence to OSS-CRS conventions, using multi-stage Docker builds for tooling, and comprehensive validation before each phase transition.

## Key Findings

### Recommended Stack

OSS-CRS prescribes most technology choices with minimal deviation room. The stack centers on Python 3.12 with uv for package management, Docker Buildx Bake for multi-image orchestration, and OpenAI-compatible LLM clients pointing to the framework-provided LiteLLM proxy.

**Core technologies:**
- **Python 3.12 + uv**: Runtime and package management — OSS-CRS standard, matches existing seedgen, faster than pip
- **Docker Buildx Bake (HCL)**: Multi-stage image builds — required by OSS-CRS prepare phase, replaces Makefile approaches
- **langgraph + langchain-openai**: LLM workflow orchestration — existing seedgen dependency, buttercup uses same pattern
- **libCRS**: CRS-to-infrastructure interface — required for all artifact submission/download and directory registration
- **Rust 1.75+, Go 1.22+, LLVM 18**: Build ARGUS, GetCov, SeedD, CallGraph — required for coverage/instrumentation tooling

**Native components to preserve:**
- ARGUS compiler wrapper (Rust) for call graph extraction
- GetCov (Rust) for coverage instrumentation
- SeedD (Go) gRPC server for coverage feedback
- These require careful LLVM version pinning (LLVM 18 from base-builder)

### Expected Features

Research identified clear table stakes vs. differentiators for OSS-CRS integration.

**Must have (table stakes):**
- `oss-crs/crs.yaml` configuration with phase definitions — framework discovery requirement
- Target build Dockerfiles producing declared outputs — compilation with CRS instrumentation
- `libCRS` installation in all containers — framework communication layer
- `libCRS download-build-output` in run phase — retrieve build artifacts
- `libCRS submit-build-output` in build phase — publish build artifacts
- `libCRS register-submit-dir seed` — continuous seed submission to framework
- Environment variable consumption — `OSS_CRS_TARGET_HARNESS`, `OSS_CRS_LLM_API_URL`, etc.

**Should have (competitive):**
- Coverage-instrumented build output — enables coverage-guided seed refinement (core differentiator)
- `compile_commands.json` generation — LSP/code analysis for LLM context enrichment
- Call graph extraction via ARGUS — function relationship analysis for LLM prompts
- Multi-module run architecture — redis + orchestrator + seedgen pattern from buttercup
- `register-shared-dir` for inter-module communication — share corpus/state between containers
- `required_llms` declaration — framework validates models available before run

**Defer (v2+):**
- Incremental builds via builder sidecar — only needed for bug-fixing CRSs, seedgen is bug-finding
- SARIF bug-candidate output — not core to seed generation
- Delta mode support — adds complexity for diff parsing, start with full mode
- Multi-language support beyond C/C++ — scope creep for initial integration

### Architecture Approach

The architecture transitions from distributed microservices to a three-phase containerized model with strict component isolation and filesystem-based communication.

**Major components:**

1. **Prepare Phase (docker buildx bake)** — Builds CRS-specific Docker images containing ARGUS, GetCov, SeedD, and seedgen Python runtime with all dependencies pre-installed

2. **Build-Target Phase (parallel builders)** — Three independent builders run in parallel: (a) asan-builder produces standard ASan binary with task structure, (b) coverage-builder produces source coverage instrumented binary, (c) compile-commands-builder generates JSON compilation database. All outputs submitted via `libCRS submit-build-output`.

3. **Run Phase (cooperating containers)** — Three containers communicate via shared filesystem and DNS: (a) redis provides in-memory task queue replacing RabbitMQ, (b) orchestrator reads build outputs and populates harness tasks in Redis, (c) seedgen performs LLM-driven seed generation with coverage feedback and submits seeds via `libCRS register-submit-dir`.

**Data flow pattern:**
- Build outputs flow through libCRS: build containers → `submit-build-output` → OSS_CRS_BUILD_OUT_DIR → `download-build-output` → run containers
- Seeds flow through filesystem watching: seedgen writes to `/output/seeds/` → `register-submit-dir` daemon → OSS_CRS_SUBMIT_DIR
- Task coordination flows through Redis: orchestrator pushes harness names → seedgen pops and processes
- Coverage feedback loops internally: seedgen → SeedD gRPC → GetCov instrumentation → coverage metrics → LLM context

### Critical Pitfalls

Research identified 15 pitfalls across critical/moderate/minor severity. Top 5 requiring careful attention:

1. **Incorrect Build Output Path Registration** — `crs.yaml` outputs list must exactly match `libCRS submit-build-output` dst_path arguments. Mismatch causes build to "succeed" but run phase crashes immediately with "build output not found." Prevention: validate crs.yaml outputs against all submit-build-output calls, test with `oss-crs build-target` before run phase.

2. **Missing libCRS Installation in Dockerfiles** — Every builder and runner Dockerfile needs `COPY --from=libcrs . /opt/libCRS && RUN /opt/libCRS/install.sh`. Missing installation causes "command not found: libCRS" at runtime. Multi-stage builds can lose libCRS between stages.

3. **Environment Variable Mapping Mismatch for LLM Access** — Existing seedgen expects custom env vars (LITELLM_URL, LITELLM_KEY) but OSS-CRS provides OSS_CRS_LLM_API_URL and OSS_CRS_LLM_API_KEY. Must create explicit mapping in entrypoint script or update Python code to read OSS-CRS variables directly.

4. **Blocking on Missing RabbitMQ/PostgreSQL Infrastructure** — Ported code may still try to connect to infrastructure that doesn't exist in OSS-CRS. Container hangs waiting for RabbitMQ or crashes on import-time database connection. Must audit and remove/stub all infrastructure dependencies before porting.

5. **Seed Submission Directory Not Registered** — Seeds generated but never appear because `libCRS register-submit-dir` not called or not backgrounded correctly. Must register in entrypoint with `libCRS register-submit-dir seed /output/seeds &` and ensure seedgen writes to registered directory.

## Implications for Roadmap

Based on research, suggested phase structure follows dependency order: prepare infrastructure → build capabilities → run integration → optimization.

### Phase 1: OSS-CRS Foundation
**Rationale:** Table stakes before any CRS functionality works. OSS-CRS validates crs.yaml structure, Dockerfiles, and HCL before allowing build/run phases. Dependencies are non-negotiable prerequisites.

**Delivers:**
- `oss-crs/crs.yaml` with all phase definitions
- `oss-crs/docker-bake.hcl` for prepare phase
- Directory structure following OSS-CRS conventions
- Python package restructure (seedgen2/ → seedgen/ with pyproject.toml)

**Addresses:**
- Table stakes: crs.yaml configuration, prepare_phase.hcl (from FEATURES.md)
- Must avoid: Pitfall #6 (Docker build context issues)

**Avoids:**
- Build context path mismatches by establishing correct structure upfront
- Late discovery of missing table stakes

**Research flag:** Low complexity, well-documented patterns from reference CRSs. Skip `/gsd:research-phase`.

### Phase 2: Build-Target Implementation
**Rationale:** Run phase depends on build outputs existing. Must validate all three build types (ASan, coverage, compile_commands) work independently before attempting run phase integration.

**Delivers:**
- `builder.Dockerfile` for standard ASan build with task structure
- `builder-coverage.Dockerfile` for source coverage instrumentation
- `builder-compile-commands.Dockerfile` for compilation database
- Build scripts (`build-*.sh`) that call `libCRS submit-build-output` correctly
- ARGUS, GetCov integration into build process

**Uses:**
- Docker Buildx Bake for multi-builder orchestration
- OSS-Fuzz base-builder image
- Rust/Cargo for ARGUS/GetCov
- LLVM 18 for CallGraph pass

**Implements:**
- Multi-builder pattern from ARCHITECTURE.md
- Parallel builds with no dependencies between them

**Addresses:**
- Table stakes: target build Dockerfiles, libCRS build output flow (from FEATURES.md)
- Differentiator: coverage-instrumented build (high value for seedgen)

**Avoids:**
- Pitfall #1 (output path mismatch) via validation script
- Pitfall #2 (missing libCRS) via standard installation block
- Pitfall #9 (ARGUS/GetCov build failures) via LLVM version pinning

**Research flag:** Medium complexity. ARGUS/GetCov integration may need `/gsd:research-phase` for LLVM pass compilation if issues arise.

### Phase 3: Infrastructure Removal
**Rationale:** Must strip out RabbitMQ/PostgreSQL dependencies before attempting OSS-CRS run phase. Doing this early prevents blocking later work.

**Delivers:**
- Audit of all infrastructure dependencies in existing seedgen
- Removal of RabbitMQ client code
- Removal of PostgreSQL session management
- Stubbing/adaptation of database models to in-memory or file-based storage
- Environment variable migration plan

**Addresses:**
- Anti-features: RabbitMQ, PostgreSQL (from FEATURES.md)

**Avoids:**
- Pitfall #4 (blocking on missing infrastructure) by removing dependencies upfront
- Import-time crashes from hardcoded connection strings

**Research flag:** Low complexity, straightforward code removal. Skip `/gsd:research-phase`.

### Phase 4: Run Phase Foundation
**Rationale:** Establish basic run phase structure with Redis orchestration before porting complex seedgen logic. Validates container communication and libCRS integration.

**Delivers:**
- `runner.Dockerfile` with redis, libCRS, Python runtime
- Entrypoint script with RUN_TYPE routing (redis/orchestrator/seedgen)
- Redis service configuration
- Orchestrator module: reads build outputs, populates task queue
- Service domain resolution via `libCRS get-service-domain`
- Seed submission registration via `libCRS register-submit-dir`

**Uses:**
- Redis for task queue (replaces RabbitMQ)
- libCRS for service discovery and artifact submission
- OSS-Fuzz base-runner image

**Implements:**
- Orchestrator-worker pattern from ARCHITECTURE.md
- Service domain resolution pattern
- RUN_TYPE multiplexing pattern

**Addresses:**
- Table stakes: run-phase module Dockerfile, register-submit-dir seed (from FEATURES.md)
- Differentiators: multi-module run architecture, register-shared-dir (from FEATURES.md)

**Avoids:**
- Pitfall #3 (LLM env var mismatch) via explicit mapping in entrypoint
- Pitfall #5 (seeds not submitted) via background register-submit-dir
- Pitfall #15 (Redis timing) via availability checks

**Research flag:** Medium complexity. Orchestrator logic may need `/gsd:research-phase` for task_meta.json parsing and harness enumeration.

### Phase 5: Seedgen Core Port
**Rationale:** With infrastructure (build outputs, Redis, libCRS) working, port the core seedgen LLM pipeline. This is the most complex phase requiring careful adaptation of existing code.

**Delivers:**
- Seedgen module adapted to Redis task queue
- LLM client pointing to OSS_CRS_LLM_API_URL
- Coverage feedback loop via SeedD gRPC
- Seed writing to registered submission directory
- LLM context generation from compile_commands.json and call graphs

**Uses:**
- langgraph for LLM workflow orchestration
- langchain-openai for OpenAI-compatible LLM access
- Redis for task consumption
- GetCov/SeedD for coverage feedback

**Implements:**
- Glance → Filetype → Alignment → Coverage stage pipeline
- Coverage-guided seed refinement

**Addresses:**
- Core seedgen functionality
- Differentiator: LLM integration, coverage feedback loop

**Avoids:**
- Pitfall #8 (gRPC networking) via get-service-domain and 0.0.0.0 binding

**Research flag:** High complexity. Core seedgen logic adaptation likely needs `/gsd:research-phase` for LLM prompt engineering and coverage feedback integration specifics.

### Phase 6: End-to-End Validation
**Rationale:** Validate the full pipeline with real OSS-Fuzz targets before considering advanced features. Catch integration issues early.

**Delivers:**
- Working end-to-end flow: prepare → build-target → run → seeds submitted
- Test with multiple OSS-Fuzz harnesses
- Validation script checking all libCRS integrations
- Documentation of observed issues and resolutions

**Addresses:**
- Integration validation across all three phases
- Harness name handling (Pitfall #10)

**Avoids:**
- Late discovery of fundamental integration issues
- Assuming success without real-world testing

**Research flag:** Low complexity, testing/validation work. Skip `/gsd:research-phase`.

### Phase 7: Advanced Features
**Rationale:** With core functionality proven, add differentiating features that increase seed quality but aren't strictly required.

**Delivers:**
- Call graph extraction via ARGUS for LLM context
- compile_commands.json integration into LLM prompts
- Delta mode support for targeted fuzzing
- Additional LLM model support

**Addresses:**
- Differentiators: call graph extraction, compile_commands.json (from FEATURES.md)
- Should-have: delta mode support (from FEATURES.md)

**Avoids:**
- Scope creep by deferring until core works

**Research flag:** Medium-high complexity. Call graph integration and delta mode may each need `/gsd:research-phase` for implementation specifics.

### Phase Ordering Rationale

- **Foundation before functionality:** Phase 1 establishes structure, preventing rework
- **Build before run:** Phase 2 creates artifacts that Phase 4-5 consume; validates isolation
- **Infrastructure removal early:** Phase 3 unblocks run phase work, prevents false dependencies
- **Incremental run complexity:** Phase 4 validates orchestration before Phase 5 adds LLM complexity
- **Validation before enhancement:** Phase 6 proves integration before Phase 7 adds features
- **Dependency-driven:** Each phase uses outputs from previous phases, minimizing rework

This ordering also aligns with OSS-CRS's three-phase lifecycle, validating each phase independently before integration. It follows buttercup-bugfind's proven pattern of redis + orchestrator + worker while adapting to seedgen's specific coverage-feedback requirements.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Build-Target):** ARGUS/GetCov LLVM pass compilation may have version-specific quirks requiring detailed investigation
- **Phase 4 (Run Foundation):** task_meta.json format and harness enumeration patterns need reference CRS deep-dive
- **Phase 5 (Seedgen Port):** LLM prompt engineering for coverage-guided refinement needs domain expertise research
- **Phase 7 (Advanced Features):** Call graph extraction integration and delta mode implementation both niche, sparse documentation

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** Well-documented crs.yaml and directory structure from development guide
- **Phase 3 (Infrastructure Removal):** Straightforward code deletion and stubbing
- **Phase 6 (Validation):** Testing methodology, no novel research needed

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies prescribed by OSS-CRS or verified in reference CRSs; versions pinned |
| Features | HIGH | Clear table stakes vs differentiators from framework requirements and buttercup reference |
| Architecture | HIGH | Three-phase model well-documented; buttercup provides direct parallel for seed generation CRS |
| Pitfalls | HIGH | Identified from reference CRS source code examination and official development guide warnings |

**Overall confidence:** HIGH

Research is based on official OSS-CRS documentation, three diverse reference CRS implementations (simple: crs-libfuzzer, complex: atlantis-multilang, seedgen-like: buttercup-bugfind), and libCRS source code examination. The existing seedgen codebase is also well-mapped in `.planning/codebase/`, providing clear understanding of what needs adaptation.

### Gaps to Address

Despite high overall confidence, several areas need validation during implementation:

- **ARGUS/GetCov LLVM version compatibility:** Reference CRSs use LLVM 18 from base-builder, but seedgen's existing components may have been tested with different versions. Build failures in Phase 2 may require version negotiation or patching.

- **SeedD gRPC inter-container communication:** Existing seedgen likely runs SeedD locally; containerized deployment needs validation of gRPC over Docker network. May need SeedD as separate module in crs_run_phase vs. embedded in seedgen container.

- **Coverage feedback loop timing:** Unclear if existing seedgen expects synchronous or asynchronous coverage results. OSS-CRS's container model may introduce latency requiring buffering or callback adaptation.

- **LLM context size limits:** Existing seedgen may pass unbounded context (full source, compile_commands.json, call graphs) to LLMs. OSS-CRS's LiteLLM proxy may have token limits requiring chunking or summarization.

- **Harness enumeration edge cases:** OSS-Fuzz projects have varying harness naming patterns. Phase 4 orchestrator needs robust harness discovery that handles: multiple harnesses, harness_name vs. harness_binary mismatches, missing task_meta.json fields.

**Mitigation strategies:**
- For LLVM compatibility: Use multi-stage Docker builds to isolate tooling compilation; pin exact commits; add version detection to fail fast if mismatch
- For gRPC communication: Prototype service-domain resolution in Phase 4 before full seedgen port
- For coverage timing: Instrument with logging to measure latency; add async buffering if needed
- For LLM context: Implement context size monitoring and truncation strategy in Phase 5
- For harness enumeration: Test orchestrator with diverse OSS-Fuzz projects in Phase 6; add fallback heuristics

## Sources

### Primary (HIGH confidence)
- `/home/andrew/post/oss-crs-6/docs/crs-development-guide.md` — OSS-CRS official development guide with phase requirements, libCRS API usage
- `/home/andrew/post/oss-crs-6/docs/design/libCRS.md` — libCRS API reference with all commands and environment variables
- `/home/andrew/post/oss-crs-6/README.md` — OSS-CRS overview with architecture and CRS integration flow
- `/home/andrew/post/crs-libfuzzer/oss-crs/crs.yaml` — Simple reference CRS for baseline patterns
- `/home/andrew/post/buttercup-bugfind/oss-crs/` — Seed generation CRS with redis + orchestrator + worker pattern
- `/home/andrew/post/buttercup-bugfind/oss-crs/orchestrator.py` — Task queue population logic
- `/home/andrew/post/buttercup-bugfind/oss-crs/bin/buttercup_entrypoint` — RUN_TYPE routing and env var mapping
- `/home/andrew/post/atlantis-multilang-wo-concolic/oss-crs/crs.yaml` — Complex multi-module CRS with LLM integration

### Secondary (MEDIUM confidence)
- `/home/andrew/post/oss-crs-6/libCRS/libCRS/base.py` — libCRS implementation details
- `/home/andrew/post/oss-crs-6/libCRS/libCRS/local.py` — Local backend for submit/download operations
- `/home/andrew/post/42-seedgen/.planning/codebase/CONCERNS.md` — Existing seedgen known issues and technical debt
- `/home/andrew/post/42-seedgen/.planning/codebase/COMPONENT_MAP.md` — Component dependency mapping

### Tertiary (LOW confidence, needs validation)
- OSS-Fuzz documentation (assumed but not directly examined) — Harness naming conventions, task structure
- LiteLLM proxy behavior (inferred from reference CRSs) — Token limits, model routing

---
*Research completed: 2026-03-12*
*Ready for roadmap: yes*
