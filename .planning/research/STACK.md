# Technology Stack: OSS-CRS Integration

**Project:** 42-seedgen OSS-CRS Port
**Researched:** 2026-03-12
**Confidence:** HIGH (verified against official OSS-CRS documentation and reference implementations)

## Executive Summary

This document specifies the technology stack required to integrate the existing seedgen pipeline into OSS-CRS's three-phase architecture. The stack is largely prescribed by OSS-CRS conventions with minimal room for deviation. The primary choices involve Python packaging (uv), Docker build tooling (buildx bake), and LLM client configuration (OpenAI-compatible via LiteLLM).

---

## Recommended Stack

### Core Runtime

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | >= 3.12 | Runtime for seedgen orchestration | OSS-CRS requires >= 3.10; reference CRSs (buttercup) use 3.12; matches existing seedgen |
| uv | latest | Package management and venv creation | OSS-CRS standard; used by libCRS installer; faster than pip |
| Docker | latest | Containerization for all three phases | OSS-CRS requirement |
| Docker Buildx | latest | Multi-stage builds via HCL | Required for prepare_phase.hcl |

### Build Tools (Prepare Phase)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Docker Buildx Bake | latest | Image orchestration | OSS-CRS prepare phase requires HCL-based build definitions |
| Rust/Cargo | 1.75+ | Build ARGUS, GetCov, CallGraph runtime, Bandld | Required for coverage/instrumentation tooling |
| Go | 1.22+ | Build SeedD gRPC server | SeedD is written in Go |
| LLVM | 18 | Build CallGraph LLVM pass | OSS-Fuzz base-builder includes LLVM 18 |

### Python Dependencies (Run Phase)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| langgraph | ~=0.6.6 | LLM workflow orchestration | Used by existing seedgen pipeline; buttercup uses same |
| langchain-openai | ~=0.3.30 | OpenAI/LiteLLM client | Standard for OSS-CRS LLM access pattern |
| langchain-anthropic | ~=0.3.4 | Anthropic model support | Used by existing seedgen |
| pydantic | ~=2.12 | Configuration and data validation | OSS-CRS convention; type-safe config |
| redis | ~=5.2.1 | Inter-module shared state (optional) | Used by buttercup for module coordination |
| grpcio | ~=1.70.0 | SeedD client communication | Existing seedgen uses gRPC for coverage |
| watchdog | ~=6.0.0 | File system monitoring | libCRS dependency for register-submit-dir |
| requests | ~=2.28.0 | HTTP client for builder sidecar | libCRS dependency |

### Infrastructure Libraries

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| libCRS | 0.1.0 | CRS-to-infrastructure interface | Required by OSS-CRS; provides submit/fetch/build APIs |
| openlit | ~=1.36.0,<1.36.6 | LLM observability | Used by buttercup; note version cap due to langgraph compatibility |
| langfuse | ~=2.59.2 | LLM tracing (optional) | Used by buttercup for debugging |

### Docker Base Images

| Image | Purpose | Why |
|-------|---------|-----|
| `gcr.io/oss-fuzz-base/base-builder` | Target compilation | OSS-CRS convention for build-target phase |
| `gcr.io/oss-fuzz-base/base-runner` | CRS execution | Standard for run phase; includes fuzzing tooling |

---

## crs.yaml Configuration

Based on reference CRSs, the seedgen integration requires:

```yaml
name: seedgen
type:
  - bug-finding
version: "1.0.0"
docker_registry: ghcr.io/team/seedgen  # Replace with actual registry

prepare_phase:
  hcl: oss-crs/docker-bake.hcl

target_build_phase:
  - name: coverage-build
    dockerfile: oss-crs/dockerfiles/builder-coverage.Dockerfile
    outputs:
      - coverage/build
  - name: callgraph-build
    dockerfile: oss-crs/dockerfiles/builder-callgraph.Dockerfile
    outputs:
      - callgraph/build
      - callgraph/compile_commands.json

crs_run_phase:
  seedgen:
    dockerfile: oss-crs/dockerfiles/seedgen-runner.Dockerfile
    additional_env:
      SEEDGEN_MODE: coverage_guided

supported_target:
  mode:
    - full
    - delta
  language:
    - c
    - c++
  sanitizer:
    - address
  architecture:
    - x86_64

required_llms:
  - o4-mini
  - gpt-4.1
  - claude-sonnet-4-20250514
```

---

## Environment Variables

OSS-CRS provides these at runtime (do not hardcode):

| Variable | Description |
|----------|-------------|
| `OSS_CRS_LLM_API_URL` | LiteLLM proxy endpoint |
| `OSS_CRS_LLM_API_KEY` | Per-CRS API key |
| `OSS_CRS_BUILD_OUT_DIR` | Build output directory (read-only) |
| `OSS_CRS_SUBMIT_DIR` | Submission directory |
| `OSS_CRS_FETCH_DIR` | Fetch directory (inter-CRS exchange) |
| `OSS_CRS_SHARED_DIR` | Shared directory (intra-CRS) |
| `OSS_CRS_TARGET_HARNESS` | Target harness binary name |
| `OSS_CRS_CPUSET` | Allocated CPU cores |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Package manager | uv | pip | OSS-CRS convention; faster; better lockfiles |
| Python version | 3.12 | 3.10/3.11 | 3.12 gives better performance; buttercup uses 3.12 |
| Build orchestration | HCL (Buildx Bake) | Makefile | OSS-CRS requires HCL for prepare_phase |
| LLM client | langchain-openai | openai SDK | langgraph integration; existing seedgen uses langchain |
| Coverage tool | GetCov (existing) | LLVM's llvm-cov | GetCov already integrated; custom format for seedgen |

---

## What NOT to Use

| Technology | Reason |
|------------|--------|
| RabbitMQ | OSS-CRS handles orchestration; unnecessary complexity |
| PostgreSQL | No persistent state needed; libCRS handles artifact management |
| Kubernetes manifests | OSS-CRS handles container orchestration |
| Custom LiteLLM deployment | OSS-CRS provides `OSS_CRS_LLM_API_URL` |
| pip (for runtime) | Use uv for consistency with OSS-CRS patterns |
| requirements.txt (for packaging) | Use pyproject.toml + uv.lock |

---

## Directory Structure

Required OSS-CRS convention:

```
42-seedgen/
  oss-crs/
    crs.yaml                    # CRS configuration (required)
    docker-bake.hcl             # Prepare phase build definitions
    dockerfiles/
      builder-coverage.Dockerfile
      builder-callgraph.Dockerfile
      seedgen-runner.Dockerfile
    bin/
      build-coverage.sh         # Target build script
      build-callgraph.sh        # Target build script
      run-seedgen.sh            # Run phase entry script
  seedgen/                      # Python package (from existing seedgen2/)
    pyproject.toml
    src/
      seedgen/
        __init__.py
        ...
  components/                   # Native components (existing)
    argus/
    getcov/
    seedd/
    callgraph/
```

---

## Installation Commands

### Prepare Phase (Docker Build)

```bash
# Build all CRS images
docker buildx bake -f oss-crs/docker-bake.hcl
```

### Python Package (in Dockerfile)

```dockerfile
# Install uv (if not present)
COPY --from=ghcr.io/astral-sh/uv:0.5.20 /uv /uvx /bin/

# Create venv and install dependencies
WORKDIR /app
COPY seedgen/pyproject.toml seedgen/uv.lock ./seedgen/
RUN cd seedgen && uv sync --frozen --no-install-project

# Copy source and install
COPY seedgen/ ./seedgen/
RUN cd seedgen && uv sync --frozen
```

### libCRS Installation

```dockerfile
# Standard pattern for all CRS containers
COPY --from=libcrs . /opt/libCRS
RUN /opt/libCRS/install.sh
```

---

## LLM Client Configuration

Use OSS-CRS-provided environment variables:

```python
from openai import OpenAI
import os

def get_llm_client():
    return OpenAI(
        api_key=os.environ["OSS_CRS_LLM_API_KEY"],
        base_url=os.environ["OSS_CRS_LLM_API_URL"],
    )

# With langchain
from langchain_openai import ChatOpenAI

def get_chat_model(model_name: str = "gpt-4.1"):
    return ChatOpenAI(
        model=model_name,
        api_key=os.environ["OSS_CRS_LLM_API_KEY"],
        base_url=os.environ["OSS_CRS_LLM_API_URL"],
    )
```

---

## Confidence Assessment

| Component | Confidence | Source |
|-----------|------------|--------|
| OSS-CRS structure | HIGH | Official docs, reference CRSs |
| libCRS API | HIGH | Source code examination |
| Python versions | HIGH | Reference CRS pyproject.toml |
| LLM integration | HIGH | docs/config/llm.md |
| Native build tools | HIGH | Existing seedgen Dockerfile |
| Directory conventions | HIGH | crs-development-guide.md |

---

## Sources

- OSS-CRS Development Guide: `/home/andrew/post/oss-crs-6/docs/crs-development-guide.md`
- OSS-CRS README: `/home/andrew/post/oss-crs-6/README.md`
- libCRS Source: `/home/andrew/post/oss-crs-6/libCRS/`
- Reference CRS (crs-libfuzzer): `/home/andrew/post/crs-libfuzzer/`
- Reference CRS (buttercup-bugfind): `/home/andrew/post/buttercup-bugfind/`
- Reference CRS (atlantis-multilang): `/home/andrew/post/atlantis-multilang-wo-concolic/`
- Existing seedgen: `/home/andrew/post/42-seedgen/components/seedgen/`
