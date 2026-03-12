---
phase: 4
slug: validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | bash scripts + pytest |
| **Config file** | .planning/phases/04-validation/scripts/ |
| **Quick run command** | `./scripts/run-full-pipeline.sh` |
| **Full suite command** | `./scripts/run-full-pipeline.sh && python3 ./scripts/compare-coverage.py validation/baseline/coverage.json validation/seeds/coverage.json` |
| **Estimated runtime** | ~600 seconds (10 min pipeline + measurement) |

---

## Sampling Rate

- **After every task commit:** Run `./scripts/run-full-pipeline.sh --dry-run` (verify script syntax)
- **After every plan wave:** Run full validation suite
- **Before `/gsd:verify-work`:** Full suite must pass (pipeline completes, coverage improves)
- **Max feedback latency:** 600 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | VALD-01 | integration | `./scripts/run-full-pipeline.sh` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | VALD-02 | integration | `python3 ./scripts/compare-coverage.py baseline.json seeds.json` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `.planning/phases/04-validation/scripts/run-full-pipeline.sh` — full OSS-CRS pipeline orchestration
- [ ] `.planning/phases/04-validation/scripts/measure-baseline.sh` — baseline coverage collection
- [ ] `.planning/phases/04-validation/scripts/measure-with-seeds.sh` — seed coverage collection
- [ ] `.planning/phases/04-validation/scripts/compare-coverage.py` — coverage comparison and assertion
- [ ] OSS-Fuzz target available — afc-freerdp-delta-01 or alternative standard target (libxml2/xml)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Container images build | VALD-01 | Docker build requires local daemon | Run `docker images` and verify seedgen-* images exist |
| LLM API connectivity | VALD-01 | External service dependency | Verify OSS_CRS_LLM_API_URL is reachable |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 600s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
