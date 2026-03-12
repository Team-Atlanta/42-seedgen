# Phase 1: Prepare - Research

**Researched:** 2026-03-12
**Domain:** OSS-CRS prepare phase, Docker multi-stage builds, Rust/Go tooling compilation
**Confidence:** HIGH

## Summary

Phase 1 requires creating the OSS-CRS repository structure and building prepare-phase images that contain four tools: ARGUS (Rust compiler wrapper), GetCov (Rust coverage tool), SeedD (Go gRPC service), and libcallgraph_rt (Rust static library). The existing codebase contains working build configurations in `components/seedgen/Dockerfile` and `components/seedgen/prebuilt.dockerfile` that demonstrate proven multi-stage Docker builds for all four tools using `gcr.io/oss-fuzz-base/base-builder` as the base image.

The OSS-CRS structure requires three files: `crs.yaml` (manifest), `docker-bake.hcl` (prepare phase image definitions), and Dockerfiles. Reference implementations from buttercup-bugfind and crs-libfuzzer provide validated patterns. The prepare phase produces images that subsequent build-target phase Dockerfiles can `COPY --from=` to get the built tools.

**Primary recommendation:** Adapt the existing `components/seedgen/prebuilt.dockerfile` multi-stage pattern into separate HCL targets per the user's decision, producing a final combined runtime image with all tools installed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use separate HCL targets in docker-bake.hcl for each tool
- Benefits: Better build caching, modular rebuilds, clearer dependency graph
- Each tool (ARGUS, GetCov, SeedD, libcallgraph_rt) gets its own build target
- Match whatever LLVM version OSS-Fuzz base images use (currently LLVM 22.0.0)
- Single combined runtime image containing all tools
- HCL targets produce intermediate images, final target combines them
- Follow buttercup pattern: `oss-crs/` subdirectory for all OSS-CRS files
- Structure: `oss-crs/crs.yaml`, `oss-crs/docker-bake.hcl`, `oss-crs/dockerfiles/`

### Claude's Discretion
- Exact Dockerfile structure and build stages
- HCL target naming conventions
- Base image selection (Ubuntu vs Alpine vs Debian)
- Build optimization (parallel stages, layer caching)

### Deferred Ideas (OUT OF SCOPE)
None - discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REPO-01 | crs.yaml defines prepare, build-target, and run phases with correct schema | Validated schema from buttercup and crs-libfuzzer references |
| REPO-02 | docker-bake.hcl defines targets for building CRS dependency images | HCL patterns from reference implementations + Docker Bake docs |
| REPO-03 | Dockerfile for each phase (prepare base, builders, runner) | Existing prebuilt.dockerfile provides working multi-stage pattern |
| REPO-04 | Example compose.yaml for local testing with CRSBench target | Pattern from buttercup; requires build artifacts from Phase 2 |
| PREP-01 | ARGUS compiler wrapper built from source and available in image | Rust build: `cargo build --release`, binary at `target/release/argus` |
| PREP-02 | GetCov coverage extraction tool built from source and available in image | Rust build: `cargo build --release`, binary at `target/release/getcov` |
| PREP-03 | SeedD gRPC runtime service built from source and available in image | Go build: `CGO_ENABLED=0 go build -o bin/seedd ./cmd/seedd` |
| PREP-04 | libcallgraph_rt call graph library built and available for linkage | Rust staticlib: outputs `libcallgraph_rt.a` for linkage |
</phase_requirements>

## Standard Stack

### Core
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| gcr.io/oss-fuzz-base/base-builder | latest | Base image for building | Provides LLVM 22.0.0, clang, all build deps; matches OSS-Fuzz ecosystem |
| Rust (via rustup) | stable | Build ARGUS, GetCov, libcallgraph_rt | All three tools are Rust projects |
| Go | 1.22+ | Build SeedD | SeedD is a Go project; go.mod specifies 1.22.4 |
| Docker Buildx/Bake | latest | Multi-target image builds | OSS-CRS requires docker-bake.hcl for prepare phase |

### Supporting
| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| libCRS | provided by OSS-CRS | Artifact transfer between phases | Runtime installation in images that need submit/download |
| LLVM tools (llvm-config, llvm-cov) | 22.0.0 (from base-builder) | LLVM pass compilation, coverage | Required by callgraph LLVM pass and GetCov |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| gcr.io/oss-fuzz-base/base-builder | Ubuntu + manual LLVM install | base-builder already has correct LLVM, all fuzzing deps |
| Alpine for final image | Ubuntu/Debian | Rust binaries may need glibc; Alpine uses musl. Stick with glibc-based. |

**Installation (build dependencies):**
```bash
# Rust - installed in Dockerfile
curl https://sh.rustup.rs -sSf | bash -s -- -y

# Go - copied from golang image
COPY --from=golang:1.22 /usr/local/go /usr/local/go
```

## Architecture Patterns

### Recommended Project Structure
```
oss-crs/
├── crs.yaml                    # CRS manifest
├── docker-bake.hcl             # Prepare phase targets
├── dockerfiles/
│   ├── prepare-base.Dockerfile # Combined runtime image (prepare output)
│   ├── builder.Dockerfile      # Build-target: default ASan build
│   ├── builder-coverage.Dockerfile  # Build-target: coverage instrumentation
│   ├── builder-callgraph.Dockerfile # Build-target: callgraph linkage
│   └── runner.Dockerfile       # Run phase orchestrator
└── bin/
    └── [build/run scripts]     # Helper scripts for phases
```

### Pattern 1: Multi-Stage Docker Build with Named Stages
**What:** Use separate `FROM` stages for each tool, then combine in final stage
**When to use:** Building multiple independent Rust/Go binaries in one Dockerfile
**Example:**
```dockerfile
# Source: components/seedgen/prebuilt.dockerfile (existing, validated)
FROM gcr.io/oss-fuzz-base/base-builder AS builder_argus
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
WORKDIR /app
COPY argus/ /app/argus/
RUN cd argus && cargo build --release

FROM gcr.io/oss-fuzz-base/base-builder AS builder_getcov
# ... similar pattern

# Final stage combines all
FROM gcr.io/oss-fuzz-base/base-runner AS runtime
COPY --from=builder_argus /app/argus/target/release/argus /usr/local/bin/
COPY --from=builder_getcov /app/getcov/target/release/getcov /usr/local/bin/
# ...
```

### Pattern 2: HCL Targets with Inheritance
**What:** Define individual targets in docker-bake.hcl, use groups to build all
**When to use:** OSS-CRS prepare phase requires this pattern
**Example:**
```hcl
# Source: Docker Bake reference docs
group "default" {
  targets = ["seedgen-runtime"]
}

target "builder-argus" {
  context    = "."
  dockerfile = "oss-crs/dockerfiles/prepare-base.Dockerfile"
  target     = "builder_argus"
}

target "builder-getcov" {
  context    = "."
  dockerfile = "oss-crs/dockerfiles/prepare-base.Dockerfile"
  target     = "builder_getcov"
}

target "seedgen-runtime" {
  context    = "."
  dockerfile = "oss-crs/dockerfiles/prepare-base.Dockerfile"
  target     = "runtime"
  depends_on = ["builder-argus", "builder-getcov", "builder-seedd", "builder-callgraph"]
}
```

### Pattern 3: crs.yaml Manifest Structure
**What:** YAML manifest declaring CRS phases and supported targets
**When to use:** Required for every OSS-CRS implementation
**Example:**
```yaml
# Source: buttercup-bugfind/oss-crs/crs.yaml (reference)
name: seedgen
type:
  - seed-generation
version: "1.0.0"
docker_registry: ghcr.io/your-org/seedgen

prepare_phase:
  hcl: oss-crs/docker-bake.hcl

target_build_phase:
  - name: build-coverage
    dockerfile: oss-crs/dockerfiles/builder-coverage.Dockerfile
    outputs:
      - coverage-harness
  # ... additional builders

crs_run_phase:
  runner:
    dockerfile: oss-crs/dockerfiles/runner.Dockerfile

supported_target:
  mode:
    - full
  language:
    - c
    - c++
  sanitizer:
    - address
  architecture:
    - x86_64
```

### Anti-Patterns to Avoid
- **Single monolithic Dockerfile:** User explicitly chose separate HCL targets for better caching
- **Copying entire source directories:** Only copy necessary files to minimize build context
- **Installing Rust/Go on every stage:** Use shared base or multi-stage COPY
- **Hardcoding LLVM version:** User decided to match OSS-Fuzz base image version dynamically

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rust installation | Manual rustup setup scripts | `curl https://sh.rustup.rs -sSf \| bash -s -- -y` | Standard rustup installer handles all edge cases |
| Go installation | Manual Go download/extract | `COPY --from=golang:1.22 /usr/local/go /usr/local/go` | Docker multi-stage copy is cleaner |
| LLVM toolchain | Manual LLVM build/install | Use gcr.io/oss-fuzz-base/base-builder | Base image already has correct LLVM version |
| libCRS integration | Custom artifact transfer | `COPY --from=libcrs . /opt/libCRS && /opt/libCRS/install.sh` | OSS-CRS provides libcrs image |

**Key insight:** The existing `components/seedgen/prebuilt.dockerfile` already solves tool compilation. The work is adapting it to OSS-CRS structure, not reimplementing builds.

## Common Pitfalls

### Pitfall 1: LLVM Version Mismatch for Callgraph Pass
**What goes wrong:** SeedMindCFPass.so compiled against different LLVM than target build uses
**Why it happens:** Building the pass with wrong `llvm-config`
**How to avoid:** Build pass in same base-builder image that will be used for target builds
**Warning signs:** Runtime errors about LLVM pass API version mismatch

### Pitfall 2: Rust Static Library Linkage Issues
**What goes wrong:** libcallgraph_rt.a fails to link into harness
**Why it happens:** Missing `-lpthread`, `-ldl`, or other system deps that Rust links against
**How to avoid:** Test linkage as part of image build; check with `nm` for undefined symbols
**Warning signs:** Linker errors about undefined symbols like `pthread_*`

### Pitfall 3: Missing Debug Symbols in GetCov Binaries
**What goes wrong:** Coverage extraction fails because harness lacks debug info
**Why it happens:** Build-target phase didn't include `-g` flag
**How to avoid:** ARGUS `ProfileVisitor` adds correct flags; ensure coverage builder uses it
**Warning signs:** GetCov returns empty or incomplete coverage data

### Pitfall 4: SeedD gRPC Port Conflicts
**What goes wrong:** SeedD fails to start, port already in use
**Why it happens:** Multiple containers or processes binding same port
**How to avoid:** SeedD runs inside runner container; ensure single instance
**Warning signs:** "address already in use" errors in logs

### Pitfall 5: HCL Target Dependencies Not Building
**What goes wrong:** `docker buildx bake` fails because intermediate targets don't exist
**Why it happens:** Using `contexts = { base = "target:builder-x" }` incorrectly
**How to avoid:** Use multi-stage Dockerfile with named targets; HCL selects target to build
**Warning signs:** "target not found" or "no such image" errors

## Code Examples

Verified patterns from existing codebase:

### ARGUS Build (from prebuilt.dockerfile)
```dockerfile
# Source: components/seedgen/prebuilt.dockerfile
FROM gcr.io/oss-fuzz-base/base-builder AS builder_argus
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
WORKDIR /app
COPY argus/ /app/argus/
RUN cd argus && cargo build --release
# Output: /app/argus/target/release/argus
```

### GetCov Build (from prebuilt.dockerfile)
```dockerfile
# Source: components/seedgen/prebuilt.dockerfile
FROM gcr.io/oss-fuzz-base/base-builder AS builder_getcov
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
WORKDIR /app
COPY getcov/ /app/getcov/
RUN cd getcov && cargo build --release
# Output: /app/getcov/target/release/getcov
```

### SeedD Build (from prebuilt.dockerfile)
```dockerfile
# Source: components/seedgen/prebuilt.dockerfile
FROM gcr.io/oss-fuzz-base/base-builder AS builder_seedd
COPY --from=golang:1.22 /usr/local/go /usr/local/go
ENV PATH="/usr/local/go/bin:${PATH}"
WORKDIR /app
COPY seedd/ /app/seedd/
RUN cd seedd && make
# Output: /app/seedd/bin/seedd
```

### libcallgraph_rt Build (from prebuilt.dockerfile)
```dockerfile
# Source: components/seedgen/prebuilt.dockerfile
FROM gcr.io/oss-fuzz-base/base-builder AS builder_callgraph
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
WORKDIR /app
COPY callgraph/runtime runtime
RUN cd runtime && cargo build --release
# Output: /app/runtime/target/release/libcallgraph_rt.a
```

### Callgraph LLVM Pass Build
```dockerfile
# Source: components/seedgen/prebuilt.dockerfile
FROM gcr.io/oss-fuzz-base/base-builder AS builder_llvm_pass
WORKDIR /app
COPY callgraph/llvm /app/llvm
RUN cd llvm && ./build.sh
# build.sh uses: clang++ -fno-rtti -O3 -g $(llvm-config --cxxflags) ...
# Output: /app/llvm/SeedMindCFPass.so
```

### libCRS Installation (from buttercup reference)
```dockerfile
# Source: buttercup-bugfind/oss-crs/dockerfiles/builder.Dockerfile
COPY --from=libcrs . /opt/libCRS
RUN /opt/libCRS/install.sh
# Provides: libCRS submit-build-output, download-build-output, register-submit-dir, etc.
```

### docker-bake.hcl Structure (from references)
```hcl
# Source: Adapted from buttercup + crs-libfuzzer patterns
group "default" {
  targets = ["seedgen-runtime"]
}

target "seedgen-runtime" {
  context    = "."
  dockerfile = "oss-crs/dockerfiles/prepare-base.Dockerfile"
  target     = "runtime"
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual LLVM install | OSS-Fuzz base images | Standard practice | Use base-builder for LLVM 22.0.0 |
| Single-stage Dockerfiles | Multi-stage with named targets | Docker 17.05+ | Smaller images, better caching |
| docker build | docker buildx bake | Standard in OSS-CRS | HCL-based multi-target builds |
| Go modules via go get | Go modules with go.mod | Go 1.11+ | SeedD already uses go.mod |
| Cargo dependencies rebuilt | cargo cache mounts | Recent buildkit | Faster rebuilds with --mount=type=cache |

**Current ecosystem:**
- OSS-Fuzz base-builder: LLVM 22.0.0 (verified 2026-03-12)
- Rust: Edition 2021 (all Cargo.toml files)
- Go: 1.22.4 (SeedD go.mod)

## Open Questions

1. **LLVM Pass vs Runtime-Only Callgraph**
   - What we know: Both SeedMindCFPass.so (LLVM pass) and libcallgraph_rt.a (runtime) exist
   - What's unclear: Does build-target need the LLVM pass, or just runtime linkage?
   - Recommendation: Include both in prepare image; build-target decides which to use

2. **bandld Tool Necessity**
   - What we know: `components/seedgen/bandld/` exists in prebuilt.dockerfile builds
   - What's unclear: Is bandld required for seedgen OSS-CRS or legacy only?
   - Recommendation: Include it for completeness; omit from requirements if unused

3. **compose.yaml Testing Before Build-Target**
   - What we know: REPO-04 requires compose.yaml for local testing
   - What's unclear: Testing prepare-phase images alone doesn't prove much
   - Recommendation: Create minimal compose.yaml; full testing deferred to Phase 2

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Docker build + manual verification |
| Config file | None - Docker build is the test |
| Quick run command | `docker buildx bake -f oss-crs/docker-bake.hcl --print` |
| Full suite command | `docker buildx bake -f oss-crs/docker-bake.hcl && docker run --rm seedgen-runtime ls -la /usr/local/bin/` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REPO-01 | crs.yaml valid | smoke | `cat oss-crs/crs.yaml` (syntax check) | Wave 0 |
| REPO-02 | docker-bake.hcl valid | smoke | `docker buildx bake --print` | Wave 0 |
| REPO-03 | Dockerfiles build | integration | `docker buildx bake` | Wave 0 |
| REPO-04 | compose.yaml valid | smoke | `docker compose -f oss-crs/compose.yaml config` | Wave 0 |
| PREP-01 | ARGUS binary exists | integration | `docker run --rm seedgen-runtime which argus` | Wave 0 |
| PREP-02 | GetCov binary exists | integration | `docker run --rm seedgen-runtime which getcov` | Wave 0 |
| PREP-03 | SeedD binary exists | integration | `docker run --rm seedgen-runtime which seedd` | Wave 0 |
| PREP-04 | libcallgraph_rt.a exists | integration | `docker run --rm seedgen-runtime ls /usr/local/lib/libcallgraph_rt.a` | Wave 0 |

### Sampling Rate
- **Per task commit:** `docker buildx bake --print` (validate HCL syntax)
- **Per wave merge:** Full `docker buildx bake` build
- **Phase gate:** All tools present in final image; run `--help` or `--version` where applicable

### Wave 0 Gaps
- [ ] `oss-crs/crs.yaml` - manifest file
- [ ] `oss-crs/docker-bake.hcl` - HCL targets
- [ ] `oss-crs/dockerfiles/prepare-base.Dockerfile` - multi-stage build
- [ ] `oss-crs/compose.yaml` - local testing (minimal)

## Sources

### Primary (HIGH confidence)
- Existing `components/seedgen/Dockerfile` - verified multi-stage build patterns
- Existing `components/seedgen/prebuilt.dockerfile` - all four tool builds validated
- buttercup-bugfind/oss-crs/ - reference OSS-CRS structure
- crs-libfuzzer/oss-crs/ - simpler reference implementation
- OSS-Fuzz base-builder image (LLVM 22.0.0 verified via `docker run`)

### Secondary (MEDIUM confidence)
- [Docker Bake Reference](https://docs.docker.com/build/bake/reference/) - HCL syntax and features
- [OSS-CRS GitHub](https://github.com/sslab-gatech/oss-crs) - framework overview

### Tertiary (LOW confidence)
- None - all critical patterns verified from existing code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - OSS-Fuzz base images and existing Dockerfiles proven
- Architecture: HIGH - Reference implementations from buttercup/crs-libfuzzer
- Pitfalls: MEDIUM - Based on general LLVM/Rust experience; not project-specific validation

**Research date:** 2026-03-12
**Valid until:** 2026-04-12 (stable domain; OSS-Fuzz base image may update LLVM)
