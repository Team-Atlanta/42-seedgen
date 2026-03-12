# Roadmap: 42-seedgen OSS-CRS Port

## Overview

Port the seedgen component from the existing CRS to run standalone in OSS-CRS. Phases align directly with OSS-CRS command stages: each phase's primary success criterion is that the corresponding `oss-crs` command runs to completion. Requirements within each phase are implementation details that enable that command to succeed.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Prepare** - `oss-crs prepare` completes successfully
- [x] **Phase 2: Build-Target** - `oss-crs build-target` completes successfully
- [x] **Phase 3: Run** - `oss-crs run` completes successfully with seeds generated
- [ ] **Phase 4: Validation** - Coverage improvement demonstrated over baseline

## Phase Details

### Phase 1: Prepare
**Goal**: `oss-crs prepare` command completes successfully
**Depends on**: Nothing (first phase)
**Requirements**: REPO-01, REPO-02, REPO-03, REPO-04, PREP-01, PREP-02, PREP-03, PREP-04
**Success Criteria** (what must be TRUE):
  1. `oss-crs prepare` runs to completion without errors
  2. All prepare-phase images exist and contain required tooling (ARGUS, GetCov, SeedD, libcallgraph_rt)
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Create OSS-CRS repository structure (crs.yaml, docker-bake.hcl)
- [x] 01-02-PLAN.md — Create prepare-phase Dockerfile and build all tools

### Phase 2: Build-Target
**Goal**: `oss-crs build-target` command completes successfully
**Depends on**: Phase 1
**Requirements**: BLDG-01, BLDG-02, BLDG-03, BLDG-04
**Success Criteria** (what must be TRUE):
  1. `oss-crs build-target` runs to completion without errors
  2. Build artifacts (instrumented harness, compile_commands.json, call graph) are submitted and downloadable
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Create builder Dockerfiles and scripts (coverage, compile_commands, callgraph)
- [x] 02-02-PLAN.md — Verify builder images and human approval

### Phase 3: Run
**Goal**: `oss-crs run` command completes successfully with seeds generated
**Depends on**: Phase 2
**Requirements**: RUNF-01, RUNF-02, RUNF-03, RUNF-04, RUNF-05, SEED-01, SEED-02, SEED-03, SEED-04, SEED-05, SEED-06
**Success Criteria** (what must be TRUE):
  1. `oss-crs run` runs to completion without errors
  2. Seeds appear in submission directory (seedgen pipeline executed successfully)
**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md — Create runner Dockerfile and orchestration script (artifact download, SeedD startup, seed directories)
- [x] 03-02-PLAN.md — Integrate seedgen2 pipeline and adapt presets.py for OSS-CRS LLM
- [x] 03-03-PLAN.md — Update docker-bake.hcl and crs.yaml, build and verify runner image

### Phase 4: Validation
**Goal**: End-to-end validation proves seeds improve coverage over baseline
**Depends on**: Phase 3
**Requirements**: VALD-01, VALD-02
**Success Criteria** (what must be TRUE):
  1. Full pipeline (prepare -> build-target -> run) completes with afc-freerdp-delta-01 benchmark
  2. Generated seeds demonstrate measurable coverage improvement over empty corpus
**Plans**: 3 plans

Plans:
- [x] 04-00-PLAN.md — Create validation fixtures (mock harness, coverage JSON, sample seeds)
- [x] 04-01-PLAN.md — Create validation scripts for full pipeline execution and coverage comparison
- [ ] 04-02-PLAN.md — Gap closure: Add oss-crs dependency and execute full validation (human verification)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Prepare | 2/2 | Complete | 2026-03-12 |
| 2. Build-Target | 2/2 | Complete | 2026-03-12 |
| 3. Run | 3/3 | Complete | 2026-03-12 |
| 4. Validation | 2/3 | In Progress | - |

---
*Roadmap created: 2026-03-12*
*Granularity: coarse (4 phases)*
*Coverage: 25/25 v1 requirements mapped*
