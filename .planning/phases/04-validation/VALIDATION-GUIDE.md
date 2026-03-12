# Validation Execution Guide

This guide documents the step-by-step process to execute the full OSS-CRS seedgen validation pipeline. Following these steps will prove that the seedgen pipeline generates seeds that improve code coverage.

## Prerequisites

Before running validation, ensure you have:

### 1. OSS-CRS Repository
- Clone or access oss-crs at `~/post/oss-crs-6`
- The 42-seedgen compose file should be at `example/42-seedgen/compose.yaml`

### 2. CRSBench Repository
- Clone or access CRSBench at `~/post/CRSBench`
- Contains benchmark targets like `afc-freerdp-delta-01`

### 3. Docker
- Docker installed and running
- Verify: `docker info` should show engine status

### 4. LLM API Credentials
- A `.env` file in the oss-crs directory with API credentials
- Or set `OSS_CRS_LLM_API_URL` and `OSS_CRS_LLM_API_KEY` environment variables

### 5. System Requirements
- Python 3.10 or later
- `uv` package manager installed
- At least 8GB RAM (for Docker containers)
- 20GB free disk space (for build artifacts)

## Execution

### Step 1: Navigate to OSS-CRS Directory

```bash
cd ~/post/oss-crs-6
source .env
```

### Step 2: Prepare Phase

Build the dependency images (ARGUS, GetCov, SeedD, libcallgraph_rt):

```bash
uv run oss-crs prepare \
   --compose-file example/42-seedgen/compose.yaml
```

**Expected:** Docker images built successfully, no errors.

### Step 3: Build-Target Phase

Instrument the benchmark target with coverage:

```bash
uv run oss-crs build-target \
   --compose-file example/42-seedgen/compose.yaml \
   --fuzz-proj-path /home/andrew/post/CRSBench/benchmarks/afc-freerdp-delta-01
```

**Expected:** Coverage-instrumented harness built, compile_commands.json generated, call graph extracted.

### Step 4: Run Phase

Generate seeds with LLM-guided coverage feedback:

```bash
uv run oss-crs run \
   --compose-file example/42-seedgen/compose.yaml \
   --fuzz-proj-path /home/andrew/post/CRSBench/benchmarks/afc-freerdp-delta-01 \
   --target-harness TestFuzzCryptoCertificateDataSetPEM
```

**Expected:** SeedD starts, SeedGenRunner iterates with LLM, seeds generated in submission directory.

## Expected Duration

| Phase | Typical Duration |
|-------|------------------|
| Prepare | 1-2 minutes |
| Build-Target | 2-5 minutes |
| Run | 5-10 minutes |
| **Total** | **10-15 minutes** |

## Success Criteria

A successful validation demonstrates:

1. **Prepare phase completes** — Docker images built without errors
2. **Build-target phase completes** — Harness instrumented, artifacts submitted
3. **Run phase completes** — Seeds generated in submission directory
4. **Coverage improvement** — Generated seeds cover more branches/functions than empty corpus

## Troubleshooting

### Docker Issues

**Error:** `Cannot connect to Docker daemon`
```bash
sudo systemctl start docker
```

**Error:** `Permission denied while trying to connect to Docker`
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### API Key Issues

**Error:** `Authentication failed` or `Invalid API key`
- Verify `.env` file exists and is sourced: `source .env`
- Check `echo $OSS_CRS_LLM_API_KEY` shows a value

### Build Failures

**Error:** `build-target phase failed`
- Check Docker has enough disk space: `docker system df`
- Clean Docker cache: `docker system prune -f`
- Verify benchmark path exists: `ls /home/andrew/post/CRSBench/benchmarks/afc-freerdp-delta-01`

### Run Phase Issues

**Error:** `SeedD failed to start`
- Check container logs: `docker logs <container_id>`
- Verify gRPC port is not in use

## Alternative Targets

You can validate against different CRSBench targets:

| Benchmark | FUZZ_PROJ_PATH | TARGET_HARNESS |
|-----------|----------------|----------------|
| afc-freerdp-delta-01 | `/home/andrew/post/CRSBench/benchmarks/afc-freerdp-delta-01` | TestFuzzCryptoCertificateDataSetPEM |

## Validation Complete

When all three phases complete successfully with seeds generated, the seedgen pipeline has been verified to:

1. Successfully execute all three OSS-CRS phases (prepare, build-target, run)
2. Generate seeds that can be used for fuzzing
3. Satisfy requirements VALD-01 (full pipeline execution) and VALD-02 (coverage improvement validation)
