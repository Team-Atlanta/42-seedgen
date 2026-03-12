---
phase: 03
slug: run
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Manual integration test via oss-crs CLI |
| **Config file** | example/42-seedgen/compose.yaml |
| **Quick run command** | `docker logs <runner-container>` |
| **Full suite command** | `uv run oss-crs run --compose-file example/42-seedgen/compose.yaml` |
| **Estimated runtime** | ~300 seconds |

---

## Sampling Rate

- **After every task commit:** Verify Dockerfile syntax with `docker build --check`
- **After every plan wave:** Run oss-crs prepare + build-target to verify images
- **Before `/gsd:verify-work`:** Full oss-crs run must produce seeds
- **Max feedback latency:** 300 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 03-01-01 | 01 | 1 | RUNF-01,02,03,04,05 | integration | `oss-crs run` | pending |
| 03-02-01 | 02 | 2 | SEED-01,02,03,04,05,06 | integration | seed output check | pending |
| 03-03-01 | 03 | 3 | All | e2e | full pipeline | pending |

---

## Wave 0 Requirements

- [ ] runner.Dockerfile builds successfully
- [ ] runner.py imports seedgen2 without errors
- [ ] SeedD binary starts and responds to health checks

---

*Phase: 03-run*
*Created: 2026-03-12*
