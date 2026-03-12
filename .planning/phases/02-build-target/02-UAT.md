---
status: complete
phase: 02-build-target
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md]
started: 2026-03-12T06:30:00Z
updated: 2026-03-12T07:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Coverage Builder Dockerfile Exists and Parses
expected: File exists at oss-crs/dockerfiles/builder-coverage.Dockerfile. Contains FROM with ARG target_base_image, copies tools from seedgen-runtime, sets BANDFUZZ_PROFILE=1, and runs builder-coverage.sh.
result: pass

### 2. Compile Commands Builder Dockerfile Exists and Parses
expected: File exists at oss-crs/dockerfiles/builder-compile-commands.Dockerfile. Contains FROM with ARG target_base_image, sets GENERATE_COMPILATION_DATABASE=1, and runs builder-compile-commands.sh.
result: pass

### 3. Callgraph Builder Dockerfile Exists and Parses
expected: File exists at oss-crs/dockerfiles/builder-callgraph.Dockerfile. Contains FROM with ARG target_base_image, sets ADD_ADDITIONAL_PASSES and ADD_ADDITIONAL_OBJECTS for SeedMindCFPass.so and libcallgraph_rt.a, and runs builder-callgraph.sh.
result: pass

### 4. Builder Scripts Submit Artifacts via libCRS
expected: All three builder scripts (builder-coverage.sh, builder-compile-commands.sh, builder-callgraph.sh) exist in oss-crs/bin/ and contain calls to "libCRS submit-build-output" with appropriate artifact names.
result: pass

### 5. oss-crs prepare Completes Successfully
expected: Running oss-crs prepare with compose.yaml builds seedgen-runtime and oss-crs-infra images without errors.
result: pass

### 6. oss-crs build-target Completes Successfully
expected: Running oss-crs build-target produces all three artifacts: coverage-harness, compile-commands, and callgraph.
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
