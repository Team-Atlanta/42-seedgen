# 42-seedgen OSS-CRS Port

## What This Is

Port of the seedgen component from the existing CRS to run standalone in OSS-CRS. The seedgen pipeline uses LLM-driven code generation with coverage-guided feedback to produce high-quality fuzzing seeds for OSS-Fuzz harnesses.

## Core Value

Generate seeds that maximize code coverage through iterative LLM refinement guided by runtime coverage feedback.

## Requirements

### Validated

Existing seedgen capabilities proven in the current CRS:

- ✓ Multi-stage seed generation (glance → filetype → alignment → coverage) — existing
- ✓ Coverage feedback loop via SeedD/GetCov integration — existing
- ✓ Call graph extraction for function relationship analysis — existing
- ✓ ARGUS compiler wrapper for instrumentation injection — existing
- ✓ Multi-model LLM orchestration (o3-mini, claude-3.5-sonnet, gpt-4o) — existing
- ✓ Support for C/C++ targets via LLVM toolchain — existing

### Active

OSS-CRS integration work:

- [ ] Prepare phase: Build ARGUS/GetCov/SeedD from source
- [ ] Build-target phase: Coverage-instrumented harness compilation
- [ ] Build-target phase: compile_commands.json generation
- [ ] Build-target phase: Call graph runtime library linkage
- [ ] Run phase: Direct Python seedgen orchestration (no RabbitMQ/PostgreSQL)
- [ ] Run phase: LiteLLM integration via OSS_CRS_LLM_API_URL
- [ ] Run phase: Seed export via libCRS register-submit-dir
- [ ] Run phase: Optional seed import via libCRS register-fetch-dir
- [ ] Validation: End-to-end test with afc-freerdp-delta-01 benchmark

### Out of Scope

- RabbitMQ/PostgreSQL infrastructure — OSS-CRS provides simpler orchestration
- Kubernetes deployment — OSS-CRS handles container orchestration
- Gateway/Scheduler components — only seedgen pipeline needed
- LiteLLM deployment — OSS-CRS provides OSS_CRS_LLM_API_URL
- Java/JVM target support — focus on C/C++ initially

## Context

**Existing Architecture:**
The current CRS uses a distributed microservices architecture with RabbitMQ message queues and PostgreSQL. The seedgen component (`components/seedgen/`) is a Python service that:

1. Receives tasks via RabbitMQ queue
2. Runs multi-stage LLM pipeline (seedgen2/seedgen.py)
3. Uses SeedD gRPC server for coverage collection
4. Uses GetCov for LLVM coverage extraction
5. Stores results in PostgreSQL

**OSS-CRS Integration:**
OSS-CRS has three phases:
- **Prepare**: Build CRS-specific Docker images (tooling)
- **Build-target**: Instrument the target project
- **Run**: Execute the CRS against instrumented target

**Key Components to Port:**
- `components/seedgen/seedgen2/` — Main generation pipeline
- `components/seedgen/argus/` — Compiler wrapper
- `components/seedgen/getcov/` — Coverage extraction
- `components/seedgen/seedd/` — gRPC runtime service

## Constraints

- **Architecture**: Must fit OSS-CRS three-phase model (prepare/build-target/run)
- **LLM Access**: Use OSS_CRS_LLM_API_URL and OSS_CRS_LLM_API_KEY (not custom LiteLLM)
- **Build Artifacts**: Transfer via libCRS submit-build-output / download-build-output
- **Seed Output**: Export via libCRS register-submit-dir seed
- **Validation Target**: afc-freerdp-delta-01 from CRSBench

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Direct Python orchestration | Simpler than RabbitMQ, OSS-CRS handles task lifecycle | — Pending |
| Build from source | Reproducible, no dependency on pre-built binaries | — Pending |
| Same LLM models | Proven configuration, minimal changes to seedgen logic | — Pending |
| Multiple build-target builders | Separate coverage/compile_commands/callgraph concerns | — Pending |

---
*Last updated: 2026-03-11 after initialization*
