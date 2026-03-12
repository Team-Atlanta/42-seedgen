# Requirements: 42-seedgen OSS-CRS Port

**Defined:** 2026-03-11
**Core Value:** Generate seeds that maximize code coverage through iterative LLM refinement guided by runtime coverage feedback.

## v1 Requirements

Requirements for initial OSS-CRS integration. Each maps to roadmap phases.

### Repository Structure

- [ ] **REPO-01**: crs.yaml defines prepare, build-target, and run phases with correct schema
- [ ] **REPO-02**: docker-bake.hcl defines targets for building CRS dependency images
- [ ] **REPO-03**: Dockerfile for each phase (prepare base, builders, runner)
- [ ] **REPO-04**: Example compose.yaml for local testing with CRSBench target

### Prepare Phase

- [ ] **PREP-01**: ARGUS compiler wrapper built from source and available in image
- [ ] **PREP-02**: GetCov coverage extraction tool built from source and available in image
- [ ] **PREP-03**: SeedD gRPC runtime service built from source and available in image
- [ ] **PREP-04**: libcallgraph_rt call graph library built and available for linkage

### Build-Target Phase

- [ ] **BLDG-01**: Coverage builder produces instrumented harness with -fprofile-instr-generate
- [ ] **BLDG-02**: compile_commands.json builder extracts compilation database
- [ ] **BLDG-03**: Call graph builder links harness with libcallgraph_rt
- [ ] **BLDG-04**: All builders export artifacts via libCRS submit-build-output

### Run Phase Infrastructure

- [ ] **RUNF-01**: Runner downloads build artifacts via libCRS download-build-output
- [ ] **RUNF-02**: Runner uses OSS_CRS_LLM_API_URL and OSS_CRS_LLM_API_KEY for LLM access
- [ ] **RUNF-03**: Runner exports seeds via libCRS register-submit-dir seed
- [ ] **RUNF-04**: Runner imports seeds via libCRS register-fetch-dir (optional)
- [ ] **RUNF-05**: SeedD gRPC service runs inside container for coverage collection

### Seedgen Pipeline

- [ ] **SEED-01**: Glance stage generates initial Python generator script from harness
- [ ] **SEED-02**: Filetype stage detects file format and enhances generator
- [ ] **SEED-03**: Alignment stage documents structure requirements and aligns script
- [ ] **SEED-04**: Coverage stage iteratively improves script based on coverage feedback
- [ ] **SEED-05**: Multi-model LLM orchestration (o3-mini, claude-3.5-sonnet, gpt-4o)
- [ ] **SEED-06**: Call graph extraction for function relationship analysis

### Validation

- [ ] **VALD-01**: End-to-end test passes with afc-freerdp-delta-01 benchmark
- [ ] **VALD-02**: Seeds demonstrate coverage improvement over baseline

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Features

- **ADV-01**: Delta mode support (incremental from existing seeds)
- **ADV-02**: Java/JVM target support
- **ADV-03**: Multiple harness parallel processing
- **ADV-04**: Crash triage integration

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| RabbitMQ infrastructure | OSS-CRS provides simpler orchestration; unnecessary complexity |
| PostgreSQL database | File-based state sufficient for single-run CRS |
| Kubernetes deployment | OSS-CRS handles container orchestration |
| Gateway/Scheduler components | Only seedgen pipeline needed |
| LiteLLM deployment | OSS-CRS provides OSS_CRS_LLM_API_URL |
| Custom web API | OSS-CRS provides task lifecycle management |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| REPO-01 | TBD | Pending |
| REPO-02 | TBD | Pending |
| REPO-03 | TBD | Pending |
| REPO-04 | TBD | Pending |
| PREP-01 | TBD | Pending |
| PREP-02 | TBD | Pending |
| PREP-03 | TBD | Pending |
| PREP-04 | TBD | Pending |
| BLDG-01 | TBD | Pending |
| BLDG-02 | TBD | Pending |
| BLDG-03 | TBD | Pending |
| BLDG-04 | TBD | Pending |
| RUNF-01 | TBD | Pending |
| RUNF-02 | TBD | Pending |
| RUNF-03 | TBD | Pending |
| RUNF-04 | TBD | Pending |
| RUNF-05 | TBD | Pending |
| SEED-01 | TBD | Pending |
| SEED-02 | TBD | Pending |
| SEED-03 | TBD | Pending |
| SEED-04 | TBD | Pending |
| SEED-05 | TBD | Pending |
| SEED-06 | TBD | Pending |
| VALD-01 | TBD | Pending |
| VALD-02 | TBD | Pending |

**Coverage:**
- v1 requirements: 25 total
- Mapped to phases: 0
- Unmapped: 25 ⚠️

---
*Requirements defined: 2026-03-11*
*Last updated: 2026-03-11 after initial definition*
