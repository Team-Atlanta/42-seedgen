---
phase: 02-build-target
plan: 01
subsystem: infra
tags: [docker, argus, coverage, llvm, callgraph, compile-commands, oss-crs]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: ARGUS compiler wrapper, SeedMindCFPass.so, libcallgraph_rt.a in seedgen-runtime
provides:
  - Coverage builder Dockerfile and script (BANDFUZZ_PROFILE=1)
  - Compile commands builder for compile_commands.json generation
  - Callgraph builder with SeedMindCFPass.so and libcallgraph_rt.a linkage
  - All builders submit artifacts via libCRS submit-build-output
affects: [03-run-phase]

# Tech tracking
tech-stack:
  added: [libCRS, ARGUS visitors]
  patterns: [builder-script pattern, ARGUS environment variable configuration]

key-files:
  created:
    - oss-crs/dockerfiles/builder-coverage.Dockerfile
    - oss-crs/dockerfiles/builder-compile-commands.Dockerfile
    - oss-crs/dockerfiles/builder-callgraph.Dockerfile
    - oss-crs/bin/builder-coverage.sh
    - oss-crs/bin/builder-compile-commands.sh
    - oss-crs/bin/builder-callgraph.sh
  modified: []

key-decisions:
  - "Use ARGUS visitors via environment variables rather than manual clang flags"
  - "Merge compile_commands JSON files in builder script, not run phase"
  - "Include llvm-profdata and llvm-cov in coverage output for self-contained analysis"

patterns-established:
  - "Builder Dockerfile pattern: ARG target_base_image, install libCRS, copy tools from seedgen-runtime, copy script, CMD"
  - "ARGUS environment variables: BANDFUZZ_PROFILE, GENERATE_COMPILATION_DATABASE, ADD_ADDITIONAL_PASSES, ADD_ADDITIONAL_OBJECTS"
  - "Artifact submission: libCRS submit-build-output <local_path> <output_name>"

requirements-completed: [BLDG-01, BLDG-02, BLDG-03, BLDG-04]

# Metrics
duration: 2min
completed: 2026-03-12
---

# Phase 2 Plan 1: Build-Target Builders Summary

**Three builder Dockerfiles and scripts for coverage instrumentation, compile_commands.json generation, and callgraph linkage using ARGUS visitors**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-12T05:23:46Z
- **Completed:** 2026-03-12T05:25:48Z
- **Tasks:** 3
- **Files created:** 6

## Accomplishments
- Coverage builder with BANDFUZZ_PROFILE=1 activating ARGUS ProfileVisitor for -fprofile-instr-generate -fcoverage-mapping
- Compile commands builder with GENERATE_COMPILATION_DATABASE=1 creating merged compile_commands.json
- Callgraph builder with ADD_ADDITIONAL_PASSES=SeedMindCFPass.so and ADD_ADDITIONAL_OBJECTS=/usr/local/lib/libcallgraph_rt.a
- All builders submit artifacts via libCRS matching crs.yaml output names exactly

## Task Commits

Each task was committed atomically:

1. **Task 1: Create coverage builder Dockerfile and script** - `a1e2694` (feat)
2. **Task 2: Create compile commands builder Dockerfile and script** - `86798e9` (feat)
3. **Task 3: Create callgraph builder Dockerfile and script** - `1a849b3` (feat)

## Files Created

- `oss-crs/dockerfiles/builder-coverage.Dockerfile` - Coverage builder inheriting from target_base_image
- `oss-crs/dockerfiles/builder-compile-commands.Dockerfile` - Compile commands builder
- `oss-crs/dockerfiles/builder-callgraph.Dockerfile` - Callgraph builder with LLVM pass and runtime
- `oss-crs/bin/builder-coverage.sh` - Build script with BANDFUZZ_PROFILE=1, submits coverage-harness
- `oss-crs/bin/builder-compile-commands.sh` - Build script with GENERATE_COMPILATION_DATABASE=1, merges JSON, submits compile-commands
- `oss-crs/bin/builder-callgraph.sh` - Build script with ADD_ADDITIONAL_PASSES and ADD_ADDITIONAL_OBJECTS, submits callgraph

## Decisions Made
- Used ARGUS environment variables per research rather than manual clang flags for better LLVM version compatibility
- Merge individual compile_commands JSON files in builder script using shell loop with sed for trailing comma handling
- Include llvm-profdata and llvm-cov in coverage output so run phase has self-contained coverage analysis tools

## Deviations from Plan

None - plan executed exactly as written

## Issues Encountered

- shellcheck not initially installed - installed via apt-get (blocking issue resolved per Rule 3)

## User Setup Required

None - no external service configuration required

## Next Phase Readiness
- All 3 builders ready for `oss-crs build-target` integration testing
- crs.yaml already declares these builders with correct output names
- Run phase can consume coverage-harness, compile-commands, and callgraph artifacts

---
*Phase: 02-build-target*
*Completed: 2026-03-12*
