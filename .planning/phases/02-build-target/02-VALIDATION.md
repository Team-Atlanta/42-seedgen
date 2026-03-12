---
phase: 2
slug: build-target
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Docker build + shell validation |
| **Config file** | oss-crs/crs.yaml |
| **Quick run command** | `docker build -f oss-crs/dockerfiles/builder-coverage.Dockerfile --build-arg target_base_image=gcr.io/oss-fuzz-base/base-builder .` |
| **Full suite command** | `oss-crs build-target` with CRSBench test target |
| **Estimated runtime** | ~180 seconds (full build-target with test project) |

---

## Sampling Rate

- **After every task commit:** Dockerfile syntax validation, script shellcheck
- **After every plan wave:** Docker build for each builder
- **Before `/gsd:verify-work`:** Full build-target with test target must complete
- **Max feedback latency:** 60 seconds per builder

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | BLDG-01 | smoke | `test -f oss-crs/dockerfiles/builder-coverage.Dockerfile && test -f oss-crs/bin/builder-coverage.sh` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | BLDG-02 | smoke | `test -f oss-crs/dockerfiles/builder-compile-commands.Dockerfile && test -f oss-crs/bin/builder-compile-commands.sh` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | BLDG-03 | smoke | `test -f oss-crs/dockerfiles/builder-callgraph.Dockerfile && test -f oss-crs/bin/builder-callgraph.sh` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | BLDG-04 | integration | `docker build -f oss-crs/dockerfiles/builder-coverage.Dockerfile --build-arg target_base_image=gcr.io/oss-fuzz-base/base-builder .` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `oss-crs/dockerfiles/builder-coverage.Dockerfile` — coverage builder Dockerfile
- [ ] `oss-crs/dockerfiles/builder-compile-commands.Dockerfile` — compile_commands builder Dockerfile
- [ ] `oss-crs/dockerfiles/builder-callgraph.Dockerfile` — callgraph builder Dockerfile
- [ ] `oss-crs/bin/builder-coverage.sh` — coverage build script
- [ ] `oss-crs/bin/builder-compile-commands.sh` — compile_commands build script
- [ ] `oss-crs/bin/builder-callgraph.sh` — callgraph build script

*All files created during execution; validation is the Docker build itself.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Coverage harness generates .profraw | BLDG-01 | Requires running instrumented binary | Run harness with `LLVM_PROFILE_FILE=test.profraw`, verify file created |
| Callgraph harness creates callgraph.log | BLDG-03 | Requires running instrumented binary | Run harness with `EXPORT_CALLS=1`, verify `/tmp/callgraph.log` created |

*Integration tests require a real OSS-Fuzz target build.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
