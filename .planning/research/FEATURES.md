# Feature Landscape: OSS-CRS Integration

**Domain:** CRS Integration for Seed Generation System
**Researched:** 2026-03-12
**Confidence:** HIGH (based on official OSS-CRS documentation and reference implementations)

## Table Stakes

Features users (OSS-CRS framework) expect. Missing = integration fails validation.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `oss-crs/crs.yaml` configuration | Required by framework for CRS discovery | Low | Must define name, type, phases, supported targets |
| `prepare_phase.hcl` Docker bake file | Framework builds images via `docker buildx bake` | Low | Defines build targets for all CRS images |
| Target build Dockerfile(s) | Compiles target project with CRS instrumentation | Medium | Must produce outputs declared in `crs.yaml` |
| Run-phase module Dockerfile(s) | Containerized runtime for CRS execution | Medium | Each module = separate container |
| libCRS installation in containers | Framework communication requires libCRS CLI | Low | `COPY --from=libcrs . /opt/libCRS && RUN /opt/libCRS/install.sh` |
| `libCRS download-build-output` usage | Run modules must retrieve build artifacts | Low | First step in run-phase entry script |
| `libCRS submit-build-output` usage | Build outputs must be submitted for run phase | Low | Last step in build-phase script |
| `libCRS register-submit-dir seed` | Framework expects seed output via this mechanism | Low | Background daemon watches directory |
| Environment variable consumption | CRS must use framework-provided env vars | Low | `OSS_CRS_TARGET_HARNESS`, `OSS_CRS_LLM_API_URL`, etc. |
| `supported_target` declaration | Framework validates CRS capabilities against target | Low | Languages, sanitizers, architectures, modes |

## Differentiators

Features that set this CRS apart. Not expected, but add competitive value.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Coverage-instrumented build output | Enables coverage-guided seed refinement | Medium | Separate build step with `SANITIZER=coverage` |
| `compile_commands.json` generation | LSP/code analysis for seedgen context | Medium | Via Bear or CMake export |
| Call graph extraction | Function relationship analysis for LLM context | High | ARGUS compiler wrapper integration |
| Multiple build steps | Parallel/sequential builds for different purposes | Low | Framework supports `depends_on` |
| Multi-module run architecture | Specialized containers (redis, orchestrator, coverage-bot) | Medium | Like buttercup: redis + orchestrator + coverage-bot + seed-gen |
| `register-shared-dir` for inter-module communication | Share corpus/state between modules | Low | Symlink to shared filesystem |
| `get-service-domain` for module discovery | HTTP/gRPC between CRS modules | Low | DNS resolution for service mesh |
| `required_llms` declaration | LLM validation before run | Low | Framework validates models are available |
| `register-fetch-dir seed` usage | Consume seeds from other CRSs in ensemble | Low | Enables ensemble seed sharing |
| Incremental builds via builder sidecar | Fast patch-build-test cycles | High | Only needed for bug-fixing CRSs |
| SARIF bug-candidate output | Standardized vulnerability reporting | Medium | Framework has `libCRS/sarif.py` reference |
| Delta mode support | Targeted fuzzing for changed code | Medium | `mode: delta` in supported_target |
| `libCRS fetch diff` integration | Directed fuzzing based on reference diff | Low | For delta-mode targets |

## Anti-Features

Features to explicitly NOT build for OSS-CRS integration.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| RabbitMQ message queue | OSS-CRS provides simpler orchestration | Direct Python orchestration within container |
| PostgreSQL database | No persistent cross-run state needed | In-memory or file-based state within run |
| Kubernetes deployment manifests | OSS-CRS handles container orchestration | Docker Compose via crs-compose.yaml |
| Custom LiteLLM deployment | OSS-CRS provides `OSS_CRS_LLM_API_URL` | Use provided LLM proxy endpoint |
| Gateway/Scheduler microservices | Architecture for distributed CRS, not standalone | Single-container or multi-module pattern |
| Custom API authentication | OSS-CRS manages container lifecycle | Use framework-provided env vars |
| Helm charts | OSS-CRS uses Docker Compose | Docker buildx bake + Dockerfiles |
| Azure/cloud-specific integrations | OSS-CRS abstracts deployment environment | Use libCRS for all infra interactions |
| Custom telemetry/OTLP export | Not required for OSS-CRS | Structured logging to stdout |
| Persistent volume claims | OSS-CRS manages storage via SUBMIT_DIR/SHARED_DIR | Use libCRS register-submit-dir/register-shared-dir |

## Feature Dependencies

```
# Build Phase Dependencies
compile_commands.json ← target source code compilation
call_graph_extraction ← ARGUS compiler wrapper build
coverage_build ← target base image with coverage support

# Run Phase Dependencies
coverage_feedback_loop ← coverage_build output
seed_submission ← seed_generation complete
llm_context_generation ← (call_graph OR compile_commands) AND target_source

# Cross-Phase Dependencies
run_phase ← build_phase outputs (all declared outputs must exist)
```

## MVP Recommendation

**Prioritize:**

1. **crs.yaml + Dockerfiles** — Table stakes for framework recognition
   - Complexity: Low
   - Blocks: Everything else

2. **libCRS build output flow** — Table stakes for artifact transfer
   - `submit-build-output` in build phase
   - `download-build-output` in run phase
   - Complexity: Low
   - Blocks: Run phase functionality

3. **libCRS register-submit-dir seed** — Table stakes for seed export
   - Background daemon for continuous submission
   - Complexity: Low
   - Blocks: Ensemble participation

4. **Coverage-instrumented build** — Differentiator, high value
   - Separate build step with SANITIZER=coverage
   - Complexity: Medium
   - Enables: Coverage-guided seed refinement

5. **LLM integration via OSS_CRS_LLM_API_URL** — Required for LLM-powered seedgen
   - OpenAI-compatible client pointing to framework proxy
   - Complexity: Low
   - Required for: Core seedgen functionality

**Defer:**

- **Incremental builds / builder sidecar**: Only needed for bug-fixing CRSs; seedgen is bug-finding
- **Multi-module architecture**: Start with single-module, add modules if needed for performance
- **Call graph extraction**: Complex build-time instrumentation; validate without it first
- **SARIF bug-candidate output**: Not core to seed generation; add if needed for bug reporting
- **Delta mode**: Start with full mode; delta adds complexity for diff parsing

## Complexity Assessment

| Tier | Features | Total Effort |
|------|----------|--------------|
| Must Have | crs.yaml, Dockerfiles, libCRS basic flow, seed submission | ~2-3 days |
| Should Have | Coverage build, LLM integration, env var consumption | ~2-3 days |
| Could Have | compile_commands.json, multi-module, shared-dir | ~3-5 days |
| Won't Have (this milestone) | Builder sidecar, SARIF output, delta mode | Deferred |

## Sources

- `/home/andrew/post/oss-crs-6/README.md` — OSS-CRS overview
- `/home/andrew/post/oss-crs-6/docs/crs-development-guide.md` — Comprehensive CRS development guide
- `/home/andrew/post/oss-crs-6/docs/design/libCRS.md` — libCRS CLI reference
- `/home/andrew/post/oss-crs-6/libCRS/libCRS/base.py` — libCRS API definitions
- `/home/andrew/post/oss-crs-6/libCRS/libCRS/local.py` — libCRS local implementation
- `/home/andrew/post/crs-libfuzzer/oss-crs/crs.yaml` — Reference simple CRS
- `/home/andrew/post/atlantis-multilang-wo-concolic/oss-crs/crs.yaml` — Reference LLM-powered CRS
- `/home/andrew/post/buttercup-bugfind/oss-crs/crs.yaml` — Reference multi-module CRS

---

*Feature landscape analysis: 2026-03-12*
