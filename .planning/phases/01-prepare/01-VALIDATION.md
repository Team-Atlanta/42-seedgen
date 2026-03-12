---
phase: 1
slug: prepare
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Docker build + shell validation |
| **Config file** | oss-crs/docker-bake.hcl |
| **Quick run command** | `docker buildx bake -f oss-crs/docker-bake.hcl --print` |
| **Full suite command** | `docker buildx bake -f oss-crs/docker-bake.hcl && docker run --rm seedgen-runtime sh -c 'which argus getcov seedd && ls /usr/local/lib/libcallgraph_rt.a'` |
| **Estimated runtime** | ~120 seconds (full build) |

---

## Sampling Rate

- **After every task commit:** Run `docker buildx bake -f oss-crs/docker-bake.hcl --print`
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | REPO-01 | smoke | `cat oss-crs/crs.yaml` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | REPO-02 | smoke | `docker buildx bake --print` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | REPO-03 | integration | `docker buildx bake` | ❌ W0 | ⬜ pending |
| 01-01-04 | 01 | 1 | REPO-04 | smoke | `docker compose -f oss-crs/compose.yaml config` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | PREP-01 | integration | `docker run --rm seedgen-runtime which argus` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | PREP-02 | integration | `docker run --rm seedgen-runtime which getcov` | ❌ W0 | ⬜ pending |
| 01-02-03 | 02 | 1 | PREP-03 | integration | `docker run --rm seedgen-runtime which seedd` | ❌ W0 | ⬜ pending |
| 01-02-04 | 02 | 1 | PREP-04 | integration | `docker run --rm seedgen-runtime ls /usr/local/lib/libcallgraph_rt.a` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `oss-crs/crs.yaml` — CRS manifest file
- [ ] `oss-crs/docker-bake.hcl` — HCL targets for prepare phase
- [ ] `oss-crs/dockerfiles/prepare-base.Dockerfile` — multi-stage build for all tools
- [ ] `oss-crs/compose.yaml` — local testing config (minimal)

*All files created during execution; validation is the build itself.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Image layers optimized | N/A | Subjective | Review `docker history seedgen-runtime` for reasonable layer sizes |

*All phase behaviors have automated verification via Docker build success.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
