# Phase 4: Validation - Research

**Researched:** 2026-03-12
**Domain:** End-to-end OSS-CRS pipeline validation, coverage measurement, baseline comparison
**Confidence:** HIGH

## Summary

Phase 4 validates that the complete seedgen pipeline works end-to-end by running all three OSS-CRS commands (prepare, build-target, run) against a real benchmark target and measuring coverage improvement. The validation focuses on two success criteria: (1) pipeline completes without errors, and (2) generated seeds demonstrably improve coverage over an empty corpus baseline.

The validation leverages existing tooling already built into the project: LLVM's llvm-profdata and llvm-cov for coverage measurement (included in Phase 2 coverage-harness artifacts), GetCov for parsing coverage data, and SeedD's gRPC API for runtime metrics. The key insight is that coverage validation is a comparative measurement problem, not an absolute threshold problem - we measure baseline coverage (empty corpus), then measure coverage with generated seeds, and assert improvement.

**Primary recommendation:** Create validation scripts that (1) run the full OSS-CRS pipeline with afc-freerdp-delta-01 benchmark, (2) collect baseline coverage with empty corpus, (3) collect coverage with generated seeds, (4) assert measurable improvement (>0% branch or function coverage increase), and (5) log structured metrics for analysis.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VALD-01 | End-to-end test passes with afc-freerdp-delta-01 benchmark | Run `oss-crs prepare`, `oss-crs build-target`, `oss-crs run` sequentially; verify all complete successfully |
| VALD-02 | Seeds demonstrate coverage improvement over baseline | Use llvm-profdata/llvm-cov to measure baseline (empty corpus) vs. seed-generated coverage; assert branch/function coverage increase >0% |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| llvm-profdata | LLVM toolchain | Merge .profraw coverage files | Already included in Phase 2 coverage-harness artifact |
| llvm-cov | LLVM toolchain | Generate coverage reports from profdata | Already included in Phase 2 coverage-harness artifact |
| pytest | existing | Python test framework | Existing test infrastructure in seedgen2 |
| subprocess | stdlib | Run oss-crs commands | Standard Python orchestration |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json | stdlib | Parse coverage reports | Automated metric extraction |
| docker | CLI | Build and run containers | Local validation testing |
| bash | shell | Shell scripting for pipeline orchestration | CI/CD validation scripts |

### OSS-CRS Commands
| Command | Purpose | When to Use |
|---------|---------|-------------|
| `uv run oss-crs prepare --compose-file <path>` | Build prepare-phase images | Initial setup, once per validation run |
| `uv run oss-crs build-target --compose-file <path> --fuzz-proj-path <path>` | Instrument target harness | After prepare, once per target |
| `uv run oss-crs run --compose-file <path> --fuzz-proj-path <path> --target-harness <name>` | Execute seedgen pipeline | After build-target, generates seeds |

## Architecture Patterns

### Recommended Validation Structure
```
.planning/phases/04-validation/
├── scripts/
│   ├── run-full-pipeline.sh       # Main orchestration script
│   ├── measure-baseline.sh        # Baseline coverage collection
│   ├── measure-with-seeds.sh      # Seed coverage collection
│   └── compare-coverage.py        # Coverage comparison and assertion
├── 04-RESEARCH.md                 # This file
├── 04-01-PLAN.md                  # Implementation plan
└── 04-VERIFICATION.md             # Validation results

oss-crs/
└── compose.yaml                   # Already exists - OSS-CRS composition file
```

### Pattern 1: Sequential Pipeline Execution
**What:** Run prepare → build-target → run in sequence with error checking
**When to use:** Full end-to-end validation
**Example:**
```bash
#!/bin/bash
set -e  # Exit on any error

COMPOSE_FILE="./oss-crs/compose.yaml"
FUZZ_PROJ_PATH="$HOME/oss-fuzz/projects/libxml2"  # Example
TARGET_HARNESS="xml"

echo "=== Phase 1: Prepare ==="
uv run oss-crs prepare --compose-file "$COMPOSE_FILE"

echo "=== Phase 2: Build-Target ==="
uv run oss-crs build-target \
  --compose-file "$COMPOSE_FILE" \
  --fuzz-proj-path "$FUZZ_PROJ_PATH"

echo "=== Phase 3: Run ==="
uv run oss-crs run \
  --compose-file "$COMPOSE_FILE" \
  --fuzz-proj-path "$FUZZ_PROJ_PATH" \
  --target-harness "$TARGET_HARNESS"

echo "=== All phases complete ==="
```

### Pattern 2: Baseline Coverage Measurement
**What:** Run instrumented harness with empty corpus and collect coverage
**When to use:** Establish baseline before seed generation
**Example:**
```bash
#!/bin/bash
# Source: LLVM Source-based Code Coverage documentation

HARNESS="./artifacts/coverage-harness/xml_harness"
BASELINE_DIR="./validation/baseline"
mkdir -p "$BASELINE_DIR"

# Run with empty input to establish baseline
echo "" | "$HARNESS" > /dev/null 2>&1 || true

# Merge raw profiles
llvm-profdata merge -sparse default.profraw -o baseline.profdata

# Generate JSON coverage report
llvm-cov export "$HARNESS" \
  -instr-profile=baseline.profdata \
  -format=text > "$BASELINE_DIR/coverage.json"

# Extract metrics
python3 -c "
import json, sys
data = json.load(open('$BASELINE_DIR/coverage.json'))
totals = data['data'][0]['totals']
print(f\"Baseline: {totals['branches']['covered']}/{totals['branches']['count']} branches\")
print(f\"Baseline: {totals['functions']['covered']}/{totals['functions']['count']} functions\")
"
```

### Pattern 3: Seed Coverage Measurement
**What:** Run instrumented harness with generated seeds and collect coverage
**When to use:** After seed generation to measure improvement
**Example:**
```bash
#!/bin/bash
HARNESS="./artifacts/coverage-harness/xml_harness"
SEEDS_DIR="./seeds-out"
SEED_COVERAGE_DIR="./validation/seeds"
mkdir -p "$SEED_COVERAGE_DIR"

# Run harness with each seed
for seed in "$SEEDS_DIR"/*; do
  "$HARNESS" < "$seed" > /dev/null 2>&1 || true
done

# Merge all profraw files
llvm-profdata merge -sparse *.profraw -o seeds.profdata

# Generate coverage report
llvm-cov export "$HARNESS" \
  -instr-profile=seeds.profdata \
  -format=text > "$SEED_COVERAGE_DIR/coverage.json"
```

### Pattern 4: Coverage Comparison and Assertion
**What:** Compare baseline vs. seed coverage and assert improvement
**When to use:** Final validation step
**Example:**
```python
#!/usr/bin/env python3
# Source: Coverage measurement best practices

import json
import sys

def load_coverage(path):
    with open(path) as f:
        data = json.load(f)
    totals = data['data'][0]['totals']
    return {
        'branches_covered': totals['branches']['covered'],
        'branches_total': totals['branches']['count'],
        'functions_covered': totals['functions']['covered'],
        'functions_total': totals['functions']['count'],
    }

baseline = load_coverage('validation/baseline/coverage.json')
seeds = load_coverage('validation/seeds/coverage.json')

# Calculate improvements
branch_improvement = seeds['branches_covered'] - baseline['branches_covered']
function_improvement = seeds['functions_covered'] - baseline['functions_covered']

print(f"Baseline: {baseline['branches_covered']}/{baseline['branches_total']} branches")
print(f"With seeds: {seeds['branches_covered']}/{seeds['branches_total']} branches")
print(f"Improvement: +{branch_improvement} branches ({branch_improvement/max(baseline['branches_total'],1)*100:.2f}%)")

print(f"\nBaseline: {baseline['functions_covered']}/{baseline['functions_total']} functions")
print(f"With seeds: {seeds['functions_covered']}/{seeds['functions_total']} functions")
print(f"Improvement: +{function_improvement} functions ({function_improvement/max(baseline['functions_total'],1)*100:.2f}%)")

# Assert measurable improvement
assert branch_improvement > 0 or function_improvement > 0, \
    "VALIDATION FAILED: Seeds did not improve coverage over baseline"

print("\n✓ VALIDATION PASSED: Seeds demonstrate measurable coverage improvement")
sys.exit(0)
```

### Anti-Patterns to Avoid
- **Absolute thresholds:** Don't require "80% coverage" - measure relative improvement instead
- **Single-input baseline:** Don't use only one baseline input - use empty corpus for fair comparison
- **Manual verification:** Automate coverage comparison - don't rely on human inspection of reports
- **Ignoring errors:** Don't suppress oss-crs command failures - validate clean execution

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Coverage instrumentation | Custom profiling code | LLVM -fprofile-instr-generate | Already built in Phase 2, battle-tested |
| Coverage report generation | Custom coverage parser | llvm-cov export --format=text | Standard LLVM tooling, JSON output |
| Coverage data merging | Custom profraw aggregator | llvm-profdata merge | Handles incremental coverage correctly |
| Pipeline orchestration | Custom Python runner | OSS-CRS CLI commands | Standard interface, handles Docker/libCRS |

## Common Pitfalls

### Pitfall 1: Expecting High Absolute Coverage
**What goes wrong:** Validation fails because seeds only achieve 15% coverage, team expects 80%+
**Why it happens:** Unrealistic expectations - complex targets like FreeRDP have large attack surfaces
**How to avoid:** Measure relative improvement (baseline → seeds), not absolute percentage
**Warning signs:** Setting hard coverage thresholds before running validation

### Pitfall 2: Profraw File Conflicts
**What goes wrong:** Coverage data from baseline run overwrites data from seed runs
**Why it happens:** Default LLVM_PROFILE_FILE is "default.profraw", gets overwritten on each run
**How to avoid:** Use separate directories for baseline and seed coverage collection
**Warning signs:** Coverage reports show same values for baseline and seeds

### Pitfall 3: Missing libCRS Backend
**What goes wrong:** `oss-crs build-target` fails because libCRS artifact submission has no backend
**Why it happens:** OSS-CRS requires libCRS backend for artifact storage between phases
**How to avoid:** Ensure OSS-CRS environment is fully configured with libCRS backend before validation
**Warning signs:** "libCRS submit-build-output" commands fail with connection errors

### Pitfall 4: Benchmark Target Not Available
**What goes wrong:** afc-freerdp-delta-01 benchmark referenced but not locally available
**Why it happens:** Benchmark may be from external competition dataset (AIxCC), not in standard OSS-Fuzz
**How to avoid:** Use standard OSS-Fuzz target (e.g., libxml2/xml) for initial validation, or obtain benchmark
**Warning signs:** Cannot find fuzz-proj-path for afc-freerdp-delta-01

### Pitfall 5: Zero Seeds Generated
**What goes wrong:** Pipeline completes but no seeds appear in seeds-out directory
**Why it happens:** LLM API failures, SeedD startup failures, or configuration errors in Phase 3
**How to avoid:** Check runner logs for errors, verify OSS_CRS_LLM_API_URL is configured
**Warning signs:** `oss-crs run` completes quickly (< 1 minute) without seed output

### Pitfall 6: Comparing Incompatible Coverage Data
**What goes wrong:** Baseline measured with different harness binary than seed coverage
**Why it happens:** Rebuilding harness between measurements or using wrong artifact
**How to avoid:** Use same coverage-harness artifact for both baseline and seed measurements
**Warning signs:** Different total branch/function counts between baseline and seed reports

## Code Examples

### Full Validation Script
```bash
#!/bin/bash
# Full end-to-end validation for Phase 4
# Source: OSS-CRS documentation and LLVM coverage workflow

set -e  # Exit on error
set -o pipefail

COMPOSE_FILE="./oss-crs/compose.yaml"
FUZZ_PROJ_PATH="${FUZZ_PROJ_PATH:-$HOME/oss-fuzz/projects/libxml2}"
TARGET_HARNESS="${TARGET_HARNESS:-xml}"
VALIDATION_DIR="./validation"

echo "=== Starting Full Pipeline Validation ==="
echo "Compose file: $COMPOSE_FILE"
echo "Fuzz project: $FUZZ_PROJ_PATH"
echo "Target harness: $TARGET_HARNESS"

# Clean previous validation artifacts
rm -rf "$VALIDATION_DIR"
mkdir -p "$VALIDATION_DIR"/{baseline,seeds}

# Run full pipeline
echo "=== Step 1: oss-crs prepare ==="
time uv run oss-crs prepare --compose-file "$COMPOSE_FILE"

echo "=== Step 2: oss-crs build-target ==="
time uv run oss-crs build-target \
  --compose-file "$COMPOSE_FILE" \
  --fuzz-proj-path "$FUZZ_PROJ_PATH"

echo "=== Step 3: oss-crs run ==="
time uv run oss-crs run \
  --compose-file "$COMPOSE_FILE" \
  --fuzz-proj-path "$FUZZ_PROJ_PATH" \
  --target-harness "$TARGET_HARNESS" \
  --timeout 600  # 10 minute timeout for seed generation

echo "=== Step 4: Measure baseline coverage ==="
./scripts/measure-baseline.sh "$VALIDATION_DIR/baseline"

echo "=== Step 5: Measure seed coverage ==="
./scripts/measure-with-seeds.sh "$VALIDATION_DIR/seeds"

echo "=== Step 6: Compare coverage ==="
python3 ./scripts/compare-coverage.py \
  "$VALIDATION_DIR/baseline/coverage.json" \
  "$VALIDATION_DIR/seeds/coverage.json"

echo "=== ✓ VALIDATION COMPLETE ==="
```

### Parsing GetCov Output
```python
#!/usr/bin/env python3
# Source: components/seedgen/seedgen2/utils/coverage.py

import json
from dataclasses import dataclass

@dataclass
class CoverageInfo:
    covered_branches: int
    total_branches: int
    covered_functions: int
    total_functions: int

def parse_getcov_json(json_str: str) -> CoverageInfo:
    """Parse GetCov JSON output to coverage metrics."""
    response = json.loads(json_str)
    coverage = response['coverage']

    return CoverageInfo(
        covered_branches=coverage['covered_branches'],
        total_branches=coverage['total_branches'],
        covered_functions=coverage['covered_functions'],
        total_functions=coverage['total_functions'],
    )

# Usage with SeedD gRPC
from seedgen2.utils.grpc import SeedD

seedd = SeedD("localhost", "/shared")
response = seedd.get_merged_coverage("./harness_binary")
coverage = parse_getcov_json(response.coverage_json)
print(f"Coverage: {coverage.covered_branches}/{coverage.total_branches} branches")
```

### Structured Logging for Validation
```python
#!/usr/bin/env python3
import json
import sys
from datetime import datetime

def log_validation_event(event: str, **kwargs):
    """Structured logging for validation metrics."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event,
        **kwargs
    }
    print(json.dumps(entry), file=sys.stderr, flush=True)

# Usage
log_validation_event("pipeline_started", compose_file="./oss-crs/compose.yaml")
log_validation_event("prepare_complete", duration_seconds=45)
log_validation_event("baseline_coverage", branches_covered=150, branches_total=1200)
log_validation_event("seed_coverage", branches_covered=280, branches_total=1200)
log_validation_event("validation_passed", improvement_branches=130, improvement_percent=10.83)
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | bash scripts + pytest |
| Config file | .planning/phases/04-validation/scripts/ |
| Quick run command | `./scripts/run-full-pipeline.sh` |
| Full suite command | `./scripts/run-full-pipeline.sh && pytest .planning/phases/04-validation/` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VALD-01 | Full pipeline execution | integration | `./scripts/run-full-pipeline.sh` | ❌ Wave 0 |
| VALD-02 | Coverage improvement | integration | `python3 ./scripts/compare-coverage.py baseline.json seeds.json` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** N/A - Phase 4 is validation-only, no code commits
- **Per wave merge:** N/A - Single wave with validation scripts
- **Phase gate:** Full pipeline execution required before milestone completion

### Wave 0 Gaps
- [ ] `.planning/phases/04-validation/scripts/run-full-pipeline.sh` — full OSS-CRS pipeline orchestration
- [ ] `.planning/phases/04-validation/scripts/measure-baseline.sh` — baseline coverage collection
- [ ] `.planning/phases/04-validation/scripts/measure-with-seeds.sh` — seed coverage collection
- [ ] `.planning/phases/04-validation/scripts/compare-coverage.py` — coverage comparison and assertion
- [ ] OSS-Fuzz target setup — obtain afc-freerdp-delta-01 or use alternative standard target

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual coverage inspection | Automated JSON export + comparison | LLVM 8.0+ (2019) | Enables CI/CD validation |
| Absolute coverage thresholds | Relative baseline comparison | Fuzzing research 2020+ | Realistic validation criteria |
| Single fuzzer run | Incremental seed generation loop | Coverage-guided fuzzing 2021+ | Continuous improvement measurement |

**Deprecated/outdated:**
- **gcov-based coverage:** LLVM source-based coverage (llvm-cov) is now standard for LLVM-instrumented binaries
- **Manual .profraw inspection:** llvm-cov export provides structured JSON for automation

## Open Questions

1. **Where is afc-freerdp-delta-01 benchmark located?**
   - What we know: Referenced in REQUIREMENTS.md as validation target
   - What's unclear: Whether it's from AIxCC competition, OSS-Fuzz, or internal benchmark suite
   - Recommendation: Use standard OSS-Fuzz libxml2/xml target for initial validation, document benchmark source

2. **What coverage improvement is "good enough"?**
   - What we know: VALD-02 requires "measurable improvement" - any increase >0%
   - What's unclear: Whether project has internal quality targets (e.g., 10% improvement)
   - Recommendation: Start with >0% assertion, adjust based on empirical results

3. **Should validation run multiple iterations?**
   - What we know: Runner.py loops indefinitely, generates seeds continuously
   - What's unclear: How many iterations to run before measuring coverage
   - Recommendation: Run for fixed time (10 minutes) or fixed seed count (100 seeds), measure once

4. **What happens if baseline coverage is 0%?**
   - What we know: Empty corpus may produce zero coverage for some harnesses
   - What's unclear: Whether to assert absolute coverage >0% in addition to improvement
   - Recommendation: Require seeds >0% absolute coverage AND improvement over baseline (even if baseline is 0)

## Sources

### Primary (HIGH confidence)
- [LLVM Source-based Code Coverage Documentation](https://clang.llvm.org/docs/SourceBasedCodeCoverage.html) - Coverage workflow and llvm-cov usage
- [LLVM llvm-cov Command Guide](https://llvm.org/docs/CommandGuide/llvm-cov.html) - llvm-cov export and profdata merge
- Existing codebase: components/seedgen/seedgen2/utils/coverage.py - Coverage data structures
- Existing codebase: components/seedgen/getcov/README.md - GetCov tool usage
- Existing codebase: .planning/phases/02-build-target/02-VERIFICATION.md - Build-target validation patterns

### Secondary (MEDIUM confidence)
- [OSS-CRS GitHub Repository](https://github.com/sslab-gatech/oss-crs) - OSS-CRS command interface
- [libFuzzer Documentation](https://llvm.org/docs/LibFuzzer.html) - Empty corpus baseline behavior
- [Coverage-guided Fuzzing Research](https://dl.acm.org/doi/10.1145/3460319.3464795) - Seed quality metrics (2021)
- [FuzzWise: Intelligent Initial Corpus Generation](https://arxiv.org/html/2512.21440) - Seed generation validation (2024)

### Tertiary (LOW confidence - needs verification)
- AIxCC Final Competition benchmarks - afc-freerdp-delta-01 reference unverified
- OSS-CRS coverage reporting - no explicit coverage metrics documentation found

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - LLVM coverage tools already integrated in Phase 2
- Architecture: HIGH - Following established OSS-CRS and LLVM patterns
- Pitfalls: HIGH - Derived from code analysis and fuzzing research best practices
- Benchmark availability: LOW - afc-freerdp-delta-01 source unclear

**Research date:** 2026-03-12
**Valid until:** 2026-04-12 (stable tooling, validation patterns unlikely to change)
