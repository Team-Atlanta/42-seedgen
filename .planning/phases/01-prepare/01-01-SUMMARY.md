---
phase: 01-prepare
plan: 01
subsystem: infra
tags: [oss-crs, docker-bake, hcl, yaml, manifest]

# Dependency graph
requires: []
provides:
  - OSS-CRS repository structure (oss-crs/ directory)
  - CRS manifest (crs.yaml) declaring prepare, build-target, run phases
  - Docker Bake configuration (docker-bake.hcl) with 6 build targets
affects: [01-02, build-target, run]

# Tech tracking
tech-stack:
  added: [docker-buildx-bake, oss-crs-framework]
  patterns: [multi-stage-dockerfile-targets, hcl-build-configuration]

key-files:
  created:
    - oss-crs/crs.yaml
    - oss-crs/docker-bake.hcl
    - oss-crs/dockerfiles/.gitkeep
    - oss-crs/bin/.gitkeep
  modified: []

key-decisions:
  - "Separate HCL targets per tool for better build caching and modular rebuilds"
  - "Single prepare-base.Dockerfile with named stages referenced by all targets"
  - "Default group builds combined seedgen-runtime image"

patterns-established:
  - "HCL target naming: builder-{toolname} for tool targets, seedgen-runtime for combined image"
  - "All prepare targets reference oss-crs/dockerfiles/prepare-base.Dockerfile multi-stage file"

requirements-completed: [REPO-01, REPO-02]

# Metrics
duration: 1min
completed: 2026-03-12
---

# Phase 01 Plan 01: Repository Structure Summary

**OSS-CRS repository structure with crs.yaml manifest declaring three phases and docker-bake.hcl with 6 build targets for modular tool caching**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-12T04:44:48Z
- **Completed:** 2026-03-12T04:46:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created oss-crs/ directory structure with dockerfiles/ and bin/ subdirectories
- Created crs.yaml manifest declaring prepare, build-target, and run phases
- Created docker-bake.hcl with 6 targets (5 individual tool builders + combined runtime)
- Verified HCL can be parsed by docker buildx bake

## Task Commits

Each task was committed atomically:

1. **Task 1: Create oss-crs directory structure and crs.yaml manifest** - `0ff586c` (feat)
2. **Task 2: Create docker-bake.hcl with separate tool targets** - `59472fe` (feat)

## Files Created/Modified

- `oss-crs/crs.yaml` - CRS manifest declaring phases and supported targets
- `oss-crs/docker-bake.hcl` - Docker Bake targets for prepare phase image builds
- `oss-crs/dockerfiles/.gitkeep` - Placeholder for Dockerfiles (created in Plan 02)
- `oss-crs/bin/.gitkeep` - Placeholder for binary scripts

## Decisions Made

- Used separate HCL targets per tool (builder-argus, builder-getcov, builder-seedd, builder-callgraph, builder-llvm-pass) for better build caching
- All targets reference single prepare-base.Dockerfile with named stages (to be created in Plan 02)
- Default group targets seedgen-runtime for combined image output

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Repository structure complete, ready for Dockerfile implementation in Plan 02
- crs.yaml references docker-bake.hcl correctly
- docker-bake.hcl references prepare-base.Dockerfile (to be created)

---
*Phase: 01-prepare*
*Completed: 2026-03-12*

## Self-Check: PASSED

- All 4 created files verified to exist
- Both task commits (0ff586c, 59472fe) verified in git history
