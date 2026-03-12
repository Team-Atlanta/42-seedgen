---
phase: 01-prepare
plan: 02
subsystem: infra
tags: [docker, buildx, rust, go, llvm, oss-fuzz]

# Dependency graph
requires:
  - phase: 01-prepare-01
    provides: docker-bake.hcl and crs.yaml manifest
provides:
  - Multi-stage Dockerfile building all seedgen tools (ARGUS, GetCov, SeedD, libcallgraph_rt, SeedMindCFPass)
  - Runtime image with all tools at standard paths (/usr/local/bin, /usr/local/lib)
  - Local testing compose.yaml for verification
affects: [02-build-target, 03-run-seedgen]

# Tech tracking
tech-stack:
  added: [docker-buildx-bake, multi-stage-dockerfile, oss-fuzz-base-builder]
  patterns: [named-build-stages, artifact-collection-runtime]

key-files:
  created:
    - oss-crs/dockerfiles/prepare-base.Dockerfile
    - oss-crs/compose.yaml
  modified:
    - components/seedgen/callgraph/llvm/SeedMindCFPass.cpp

key-decisions:
  - "Use gcr.io/oss-fuzz-base/base-builder for all stages including runtime"
  - "Install binaries to /usr/local/bin, libraries to /usr/local/lib"
  - "Named stages match docker-bake.hcl target names for selective builds"

patterns-established:
  - "Multi-stage Dockerfile with named stages for individual tool builds"
  - "Runtime stage collects all artifacts into single image"

requirements-completed: [REPO-03, REPO-04, PREP-01, PREP-02, PREP-03, PREP-04]

# Metrics
duration: 2min
completed: 2026-03-12
---

# Phase 01 Plan 02: Prepare Phase Dockerfile Summary

**Multi-stage Dockerfile building ARGUS, GetCov, SeedD, libcallgraph_rt.a, and SeedMindCFPass.so into seedgen-runtime image**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-12T04:48:16Z
- **Completed:** 2026-03-12T04:51:04Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Created prepare-base.Dockerfile with 5 builder stages + 1 runtime stage
- Added compose.yaml for local testing and verification
- Built and verified all 5 artifacts in seedgen-runtime:latest image
- Fixed LLVM pass API compatibility with OSS-Fuzz base-builder

## Task Commits

Each task was committed atomically:

1. **Task 1: Create prepare-base.Dockerfile** - `286dac8` (feat)
2. **Task 2: Create compose.yaml** - `1dccf89` (feat)
3. **Task 3: Build and verify images** - `b5048be` (fix - includes LLVM API fix)

**Plan metadata:** (pending)

## Files Created/Modified
- `oss-crs/dockerfiles/prepare-base.Dockerfile` - Multi-stage Dockerfile with 5 builder stages and runtime collector
- `oss-crs/compose.yaml` - Local testing configuration for seedgen-runtime image
- `components/seedgen/callgraph/llvm/SeedMindCFPass.cpp` - Fixed LLVM pass callback signature

## Decisions Made
- Used gcr.io/oss-fuzz-base/base-builder as base for all stages (including runtime) to maintain OSS-Fuzz LLVM compatibility
- Installed binaries to /usr/local/bin and libraries to /usr/local/lib for standard PATH access
- Named build stages to match docker-bake.hcl targets for selective caching

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed LLVM pass callback signature for newer LLVM API**
- **Found during:** Task 3 (Build and verify prepare phase images)
- **Issue:** registerOptimizerLastEPCallback lambda missing ThinOrFullLTOPhase parameter, causing compile error with OSS-Fuzz base-builder LLVM version
- **Fix:** Added ThinOrFullLTOPhase parameter to lambda signature at SeedMindCFPass.cpp:87
- **Files modified:** components/seedgen/callgraph/llvm/SeedMindCFPass.cpp
- **Verification:** docker buildx bake completed successfully after fix
- **Committed in:** b5048be

---

**Total deviations:** 1 auto-fixed (Rule 1 bug)
**Impact on plan:** Essential fix for build to complete. No scope creep.

## Issues Encountered
None - after the LLVM fix, build completed successfully.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- seedgen-runtime:latest image available with all tools
- Ready for Phase 2 (Build-Target) to use COPY --from=seedgen-runtime
- All prepare phase success criteria met

---
*Phase: 01-prepare*
*Completed: 2026-03-12*

## Self-Check: PASSED

- FOUND: oss-crs/dockerfiles/prepare-base.Dockerfile
- FOUND: oss-crs/compose.yaml
- FOUND: 286dac8 (Task 1)
- FOUND: 1dccf89 (Task 2)
- FOUND: b5048be (Task 3)
