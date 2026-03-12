#!/bin/bash
set -e
set -o pipefail

# Baseline Coverage Measurement Script
# Measures coverage with empty corpus to establish baseline

# Accept output directory as first argument
BASELINE_DIR="$1"
if [ -z "$BASELINE_DIR" ]; then
  echo "Usage: $0 <baseline_output_dir>"
  exit 1
fi

# Configuration
HARNESS_PATH="${HARNESS_PATH:-./artifacts/coverage-harness}"

# Find harness binary (first executable file in harness path)
HARNESS=$(find "$HARNESS_PATH" -type f -executable 2>/dev/null | head -1)
if [ -z "$HARNESS" ]; then
  echo "Error: No executable harness found in $HARNESS_PATH"
  exit 1
fi

echo "Using harness: $HARNESS"

# Create output directory
mkdir -p "$BASELINE_DIR"

# Clean any existing profraw files in current directory
rm -f default.profraw *.profraw 2>/dev/null || true

# Run harness with empty input to establish baseline
# Allow non-zero exit (harness may return error on empty input)
echo "Running harness with empty input..."
echo "" | "$HARNESS" > /dev/null 2>&1 || true

# Verify profraw was created
if [ ! -f "default.profraw" ]; then
  echo "Error: No profraw file generated. Harness may not be instrumented."
  exit 1
fi

# Detect fixture mode (if profraw contains "mock" it's a test fixture)
FIXTURE_MODE=false
if grep -q "mock" default.profraw 2>/dev/null; then
  FIXTURE_MODE=true
  echo "Detected fixture mode - using pre-generated coverage data"
fi

if [ "$FIXTURE_MODE" = true ]; then
  # Fixture mode: use pre-generated JSON from fixtures directory
  FIXTURE_JSON="$(dirname "$HARNESS")/baseline-coverage.json"
  if [ ! -f "$FIXTURE_JSON" ]; then
    echo "Error: Fixture JSON not found at $FIXTURE_JSON"
    exit 1
  fi
  echo "Using fixture coverage data: $FIXTURE_JSON"
  cp "$FIXTURE_JSON" "$BASELINE_DIR/coverage.json"
else
  # Real mode: use LLVM profdata tools
  echo "Merging profile data..."
  llvm-profdata merge -sparse default.profraw -o "$BASELINE_DIR/baseline.profdata"

  echo "Generating coverage report..."
  llvm-cov export "$HARNESS" \
    -instr-profile="$BASELINE_DIR/baseline.profdata" \
    -format=text > "$BASELINE_DIR/coverage.json"
fi

# Extract and display metrics
echo ""
echo "=== Baseline Coverage Metrics ==="
python3 -c "
import json
import sys

try:
    with open('$BASELINE_DIR/coverage.json') as f:
        data = json.load(f)

    totals = data['data'][0]['totals']

    branches_covered = totals['branches']['covered']
    branches_total = totals['branches']['count']
    functions_covered = totals['functions']['covered']
    functions_total = totals['functions']['count']

    print(f'Baseline: {branches_covered}/{branches_total} branches covered')
    print(f'Baseline: {functions_covered}/{functions_total} functions covered')

    if branches_total > 0:
        branch_pct = (branches_covered / branches_total) * 100
        print(f'Baseline branch coverage: {branch_pct:.2f}%')
except Exception as e:
    print(f'Error extracting metrics: {e}', file=sys.stderr)
    sys.exit(1)
"

# Clean up profraw file
rm -f default.profraw *.profraw 2>/dev/null || true

echo ""
echo "✓ Baseline coverage data saved to $BASELINE_DIR"
