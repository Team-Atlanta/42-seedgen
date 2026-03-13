---
phase: quick-1
plan: 01
subsystem: runner
tags: [source-download, libCRS, seedd]
dependency_graph:
  requires: []
  provides: [source-code-download]
  affects: [seedd-source-serving, runner-startup]
tech_stack:
  added: []
  patterns: [libCRS-cli, subprocess-run]
key_files:
  created: []
  modified:
    - oss-crs/bin/runner.py
decisions:
  - "Download source to /src using libCRS download-source target pattern"
  - "Place download_source() call after download_artifacts() but before setup_seedd_artifacts()"
metrics:
  duration_seconds: 41
  completed: "2026-03-13T14:46:21Z"
---

# Quick 1 Plan 01: Add Source Code Download Summary

Source download via libCRS download-source target /src integrated into runner.py startup sequence.

## Objective Achieved

Added source code download to CRS runner container so SeedD can serve source files via GetRegionSource and ExtractFunctionSource gRPC methods.

## Changes Made

### Task 1: Add download_source function and integrate into runner

**Commit:** 268a756

Added `download_source()` function following the existing `download_artifacts()` pattern:
- Calls `libCRS download-source target /src`
- Logs download start/complete events using log_json
- Raises RuntimeError on failure with stderr details
- Verifies /src directory exists after download

Integrated into `main()`:
- Called after `download_artifacts()` but before `setup_seedd_artifacts()`
- Wrapped in try/except with fatal_error logging and sys.exit(1)

**Files modified:**
- `oss-crs/bin/runner.py`

## Verification Results

```bash
grep -q "download-source.*target.*/src" oss-crs/bin/runner.py && \
grep -q "download_source()" oss-crs/bin/runner.py && echo "PASS"
# Output: PASS
```

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 268a756 | feat(quick-1): add source code download to CRS runner |

## Self-Check: PASSED

- FOUND: oss-crs/bin/runner.py
- FOUND: 268a756
