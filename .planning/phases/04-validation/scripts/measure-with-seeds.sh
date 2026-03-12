#!/bin/bash
set -e
set -o pipefail

# Seeds Coverage Measurement Script
# Measures coverage with generated seeds

# Accept output directory as first argument
SEED_COVERAGE_DIR="$1"
if [ -z "$SEED_COVERAGE_DIR" ]; then
  echo "Usage: $0 <seed_coverage_output_dir>"
  exit 1
fi

# Configuration
HARNESS_PATH="${HARNESS_PATH:-./artifacts/coverage-harness}"
SEEDS_DIR="${SEEDS_DIR:-./seeds-out}"

# Find harness binary (first executable file in harness path)
HARNESS=$(find "$HARNESS_PATH" -type f -executable 2>/dev/null | head -1)
if [ -z "$HARNESS" ]; then
  echo "Error: No executable harness found in $HARNESS_PATH"
  exit 1
fi

# Verify seeds exist
if [ ! -d "$SEEDS_DIR" ] || [ -z "$(ls -A "$SEEDS_DIR" 2>/dev/null)" ]; then
  echo "Error: No seeds found in $SEEDS_DIR"
  exit 1
fi

SEED_COUNT=$(ls -1 "$SEEDS_DIR" | wc -l)
echo "Using harness: $HARNESS"
echo "Seeds directory: $SEEDS_DIR"
echo "Found $SEED_COUNT seed(s)"

# Create output directory
mkdir -p "$SEED_COVERAGE_DIR"

# Clean any existing profraw files in current directory
rm -f default.profraw *.profraw 2>/dev/null || true

# Run harness with each seed
echo "Running harness with seeds..."
for seed in "$SEEDS_DIR"/*; do
  if [ -f "$seed" ]; then
    echo "  Processing: $(basename "$seed")"
    "$HARNESS" < "$seed" > /dev/null 2>&1 || true
  fi
done

# Verify profraw files were created
PROFRAW_COUNT=$(ls -1 *.profraw 2>/dev/null | wc -l)
if [ "$PROFRAW_COUNT" -eq 0 ]; then
  echo "Error: No profraw files generated. Harness may not be instrumented."
  exit 1
fi

echo "Generated $PROFRAW_COUNT profraw file(s)"

# Detect fixture mode (if profraw contains "mock" it's a test fixture)
FIXTURE_MODE=false
if grep -q "mock" *.profraw 2>/dev/null; then
  FIXTURE_MODE=true
  echo "Detected fixture mode - using pre-generated coverage data"
fi

if [ "$FIXTURE_MODE" = true ]; then
  # Fixture mode: use pre-generated JSON from fixtures directory
  FIXTURE_JSON="$(dirname "$HARNESS")/seeds-coverage.json"
  if [ ! -f "$FIXTURE_JSON" ]; then
    echo "Error: Fixture JSON not found at $FIXTURE_JSON"
    exit 1
  fi
  echo "Using fixture coverage data: $FIXTURE_JSON"
  cp "$FIXTURE_JSON" "$SEED_COVERAGE_DIR/coverage.json"
else
  # Real mode: use LLVM profdata tools
  echo "Merging profile data..."
  llvm-profdata merge -sparse *.profraw -o "$SEED_COVERAGE_DIR/seeds.profdata"

  echo "Generating coverage report..."
  llvm-cov export "$HARNESS" \
    -instr-profile="$SEED_COVERAGE_DIR/seeds.profdata" \
    -format=text > "$SEED_COVERAGE_DIR/coverage.json"
fi

# Extract and display metrics
echo ""
echo "=== Seeds Coverage Metrics ==="
python3 -c "
import json
import sys

try:
    with open('$SEED_COVERAGE_DIR/coverage.json') as f:
        data = json.load(f)

    totals = data['data'][0]['totals']

    branches_covered = totals['branches']['covered']
    branches_total = totals['branches']['count']
    functions_covered = totals['functions']['covered']
    functions_total = totals['functions']['count']

    print(f'Seeds: {branches_covered}/{branches_total} branches covered')
    print(f'Seeds: {functions_covered}/{functions_total} functions covered')

    if branches_total > 0:
        branch_pct = (branches_covered / branches_total) * 100
        print(f'Seeds branch coverage: {branch_pct:.2f}%')
except Exception as e:
    print(f'Error extracting metrics: {e}', file=sys.stderr)
    sys.exit(1)
"

# Clean up profraw files
rm -f default.profraw *.profraw 2>/dev/null || true

echo ""
echo "✓ Seeds coverage data saved to $SEED_COVERAGE_DIR"
