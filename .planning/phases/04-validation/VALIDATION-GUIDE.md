# Validation Execution Guide

This guide documents the step-by-step process to execute the full OSS-CRS seedgen validation pipeline. Following these steps will prove that the seedgen pipeline generates seeds that improve code coverage.

## Prerequisites

Before running validation, ensure you have:

### 1. Docker
- Docker installed and running
- Verify: `docker info` should show engine status

### 2. OSS-Fuzz Repository
- Clone OSS-Fuzz to access benchmark targets
- Default location: `$HOME/oss-fuzz`
- Clone command: `git clone https://github.com/google/oss-fuzz.git ~/oss-fuzz`

### 3. LLM API Credentials
- OpenAI API key (or compatible API endpoint)
- Endpoint URL (default: `https://api.openai.com/v1`)

### 4. System Requirements
- Python 3.10 or later
- `uv` package manager installed
- At least 8GB RAM (for Docker containers)
- 20GB free disk space (for build artifacts)

## Environment Setup

### Step 1: Install Dependencies

From the project root, install the oss-crs dependency:

```bash
cd /home/andrew/post/42-seedgen
uv sync
```

This installs the `oss-crs` package which provides the CLI commands (`prepare`, `build-target`, `run`).

### Step 2: Configure LLM API

Set the required environment variables for the LLM backend:

```bash
# OpenAI (default)
export OSS_CRS_LLM_API_URL="https://api.openai.com/v1"
export OSS_CRS_LLM_API_KEY="sk-..."  # Your OpenAI API key

# Alternative: Local LLM (e.g., Ollama)
# export OSS_CRS_LLM_API_URL="http://localhost:11434/v1"
# export OSS_CRS_LLM_API_KEY="not-needed"
```

### Step 3: Configure Target Project

Set the benchmark target (defaults to libxml2/xml):

```bash
# Default configuration (libxml2)
export FUZZ_PROJ_PATH="$HOME/oss-fuzz/projects/libxml2"
export TARGET_HARNESS="xml"

# Optional: Custom timeout (default: 600 seconds)
export TIMEOUT=600
```

### Alternative Targets

You can validate against different OSS-Fuzz targets:

| Project | FUZZ_PROJ_PATH | TARGET_HARNESS |
|---------|----------------|----------------|
| libxml2 | `$HOME/oss-fuzz/projects/libxml2` | xml |
| freerdp | `$HOME/oss-fuzz/projects/freerdp` | delta |
| curl | `$HOME/oss-fuzz/projects/curl` | curl_fuzzer |

## Execution

### Run Full Pipeline Validation

Execute the complete validation with a single command:

```bash
./.planning/phases/04-validation/scripts/run-full-pipeline.sh
```

### What Each Phase Does

The script executes three OSS-CRS phases followed by validation:

1. **Prepare Phase** (~1-2 minutes)
   - Builds base Docker images with LLVM tooling
   - Sets up coverage instrumentation environment
   - Output: Docker images ready for target building

2. **Build-Target Phase** (~2-5 minutes)
   - Clones and instruments the target project
   - Compiles with coverage flags
   - Output: Coverage-instrumented harness binary

3. **Run Phase** (~5-10 minutes, configurable via TIMEOUT)
   - Starts SeedD gRPC server
   - Launches SeedGenRunner with LLM integration
   - Generates seeds iteratively with coverage feedback
   - Output: Generated seeds in `./seeds-out/`

4. **Validation Steps** (~1 minute)
   - Measures baseline coverage (empty corpus)
   - Measures coverage with generated seeds
   - Compares and asserts improvement

### Expected Duration

| Phase | Typical Duration |
|-------|------------------|
| Prepare | 1-2 minutes |
| Build-Target | 2-5 minutes |
| Run | 5-10 minutes |
| Validation | 1 minute |
| **Total** | **10-15 minutes** |

## Expected Output

### Successful Run

A successful validation produces output similar to:

```
==========================================
OSS-CRS Pipeline Validation
==========================================
Compose file: ./oss-crs/compose.yaml
Fuzz project: /home/user/oss-fuzz/projects/libxml2
Target harness: xml
Timeout: 600s
==========================================

=== Preparing validation environment ===
Validation directories created

=== Phase 1: PREPARE ===
Building prepare container...
[...prepare output...]
Prepare phase complete

=== Phase 2: BUILD-TARGET ===
Building target with coverage instrumentation...
[...build output...]
Build-target phase complete

=== Phase 3: RUN ===
Generating seeds with LLM feedback loop...
[...seed generation output...]
Run phase complete

=== Validation Step 1: Measuring Baseline Coverage ===
Baseline: 150/1200 branches covered
Baseline branch coverage: 12.50%
Baseline coverage measured

=== Validation Step 2: Measuring Coverage with Seeds ===
Found 15 seeds to measure
Seeds: 280/1200 branches covered
Seeds branch coverage: 23.33%
Seeds coverage measured

=== Validation Step 3: Comparing Coverage ===
============================================================
Coverage Comparison Results
============================================================

BRANCH COVERAGE:
  Baseline: 150/1200 (12.50%)
  With seeds: 280/1200 (23.33%)
  Improvement: +130 branches (+10.83 percentage points)

FUNCTION COVERAGE:
  Baseline: 45/200 (22.50%)
  With seeds: 78/200 (39.00%)
  Improvement: +33 functions (+16.50 percentage points)

============================================================
VALIDATION PASSED: Seeds demonstrate measurable coverage improvement

  - Branch coverage improved by 130 (10.83 percentage points)
  - Function coverage improved by 33 (16.50 percentage points)

==========================================
=== VALIDATION COMPLETE ===
==========================================
```

### Coverage Metrics

The validation measures two types of coverage:

- **Branch Coverage**: Percentage of code branches (if/else, loops) exercised
- **Function Coverage**: Percentage of functions called

A successful validation shows improvement in at least one metric.

## Troubleshooting

### Docker Issues

**Error:** `Cannot connect to Docker daemon`
```bash
# Start Docker daemon
sudo systemctl start docker
# Or on macOS, start Docker Desktop
```

**Error:** `Permission denied while trying to connect to Docker`
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker
```

### API Key Issues

**Error:** `Authentication failed` or `Invalid API key`
- Verify your API key is correct: `echo $OSS_CRS_LLM_API_KEY`
- Check endpoint URL matches your provider
- Ensure the key has sufficient credits/quota

### OSS-Fuzz Issues

**Error:** `FUZZ_PROJ_PATH does not exist`
```bash
# Clone OSS-Fuzz repository
git clone https://github.com/google/oss-fuzz.git ~/oss-fuzz
# Verify project exists
ls ~/oss-fuzz/projects/libxml2
```

### Build Failures

**Error:** `build-target phase failed`
- Check Docker has enough disk space: `docker system df`
- Clean Docker cache: `docker system prune -f`
- Verify target project builds independently

### Validation Failures

**Error:** `VALIDATION FAILED: No coverage improvement`
- This may indicate:
  - Seeds are not reaching new code paths
  - Harness has limited attack surface
  - Increase TIMEOUT to generate more seeds
  - Try a different target harness

### Verifying Individual Phases

To debug, run phases individually:

```bash
# Test prepare phase
uv run oss-crs prepare --compose-file ./oss-crs/compose.yaml

# Test build-target phase
uv run oss-crs build-target \
  --compose-file ./oss-crs/compose.yaml \
  --fuzz-proj-path "$FUZZ_PROJ_PATH"

# Test run phase
uv run oss-crs run \
  --compose-file ./oss-crs/compose.yaml \
  --fuzz-proj-path "$FUZZ_PROJ_PATH" \
  --target-harness "$TARGET_HARNESS" \
  --timeout 60  # Short timeout for testing
```

## Validation Complete

When you see `VALIDATION PASSED`, the seedgen pipeline has been verified to:

1. Successfully execute all three OSS-CRS phases (prepare, build-target, run)
2. Generate seeds that exercise new code paths
3. Demonstrate measurable coverage improvement over baseline

This satisfies requirements VALD-01 (full pipeline execution) and VALD-02 (coverage improvement validation).
