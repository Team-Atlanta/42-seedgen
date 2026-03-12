#!/bin/bash
set -e
set -o pipefail

# OSS-CRS Pipeline Validation Script
# Runs prepare → build-target → run pipeline and validates coverage improvement

# Configuration
COMPOSE_FILE="./oss-crs/compose.yaml"
FUZZ_PROJ_PATH="${FUZZ_PROJ_PATH:-$HOME/oss-fuzz/projects/libxml2}"
TARGET_HARNESS="${TARGET_HARNESS:-xml}"
VALIDATION_DIR="./validation"
TIMEOUT="${TIMEOUT:-600}"

# Script directory (for relative script calls)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "OSS-CRS Pipeline Validation"
echo "=========================================="
echo "Compose file: $COMPOSE_FILE"
echo "Fuzz project: $FUZZ_PROJ_PATH"
echo "Target harness: $TARGET_HARNESS"
echo "Timeout: ${TIMEOUT}s"
echo "=========================================="

# Clean and prepare validation directories
echo ""
echo "=== Preparing validation environment ==="
rm -rf "$VALIDATION_DIR"
mkdir -p "$VALIDATION_DIR"/{baseline,seeds}
echo "✓ Validation directories created"

# Phase 1: Prepare
echo ""
echo "=== Phase 1: PREPARE ==="
echo "Building prepare container..."
time uv run oss-crs prepare --compose-file "$COMPOSE_FILE"
echo "✓ Prepare phase complete"

# Phase 2: Build Target
echo ""
echo "=== Phase 2: BUILD-TARGET ==="
echo "Building target with coverage instrumentation..."
time uv run oss-crs build-target \
  --compose-file "$COMPOSE_FILE" \
  --fuzz-proj-path "$FUZZ_PROJ_PATH"
echo "✓ Build-target phase complete"

# Phase 3: Run
echo ""
echo "=== Phase 3: RUN ==="
echo "Generating seeds with LLM feedback loop..."
time uv run oss-crs run \
  --compose-file "$COMPOSE_FILE" \
  --fuzz-proj-path "$FUZZ_PROJ_PATH" \
  --target-harness "$TARGET_HARNESS" \
  --timeout "$TIMEOUT"
echo "✓ Run phase complete"

# Validation: Baseline Coverage
echo ""
echo "=== Validation Step 1: Measuring Baseline Coverage ==="
"$SCRIPT_DIR/measure-baseline.sh" "$VALIDATION_DIR/baseline"
echo "✓ Baseline coverage measured"

# Validation: Seeds Coverage
echo ""
echo "=== Validation Step 2: Measuring Coverage with Seeds ==="
"$SCRIPT_DIR/measure-with-seeds.sh" "$VALIDATION_DIR/seeds"
echo "✓ Seeds coverage measured"

# Validation: Compare and Assert
echo ""
echo "=== Validation Step 3: Comparing Coverage ==="
python3 "$SCRIPT_DIR/compare-coverage.py" \
  "$VALIDATION_DIR/baseline/coverage.json" \
  "$VALIDATION_DIR/seeds/coverage.json"

echo ""
echo "=========================================="
echo "=== ✓ VALIDATION COMPLETE ==="
echo "=========================================="
