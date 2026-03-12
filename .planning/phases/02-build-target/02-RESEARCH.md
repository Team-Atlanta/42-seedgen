# Phase 2: Build-Target - Research

**Researched:** 2026-03-12
**Domain:** OSS-CRS build-target phase, Docker builder patterns, LLVM instrumentation, compile_commands.json generation
**Confidence:** HIGH

## Summary

Phase 2 implements the build-target phase for seedgen OSS-CRS integration. This phase produces three distinct builder outputs: a coverage-instrumented harness for coverage feedback during run phase, a compile_commands.json compilation database for code analysis, and a callgraph-instrumented harness linking libcallgraph_rt.a for function relationship extraction.

The existing project infrastructure from Phase 1 provides all necessary tools: ARGUS compiler wrapper with ProfileVisitor and CompilationDatabaseVisitor capabilities, the SeedMindCFPass.so LLVM pass for call graph instrumentation, and libcallgraph_rt.a runtime library. The buttercup-bugfind reference implementation provides validated patterns for builder Dockerfiles and scripts using libCRS submit-build-output.

**Primary recommendation:** Create three builder Dockerfiles with corresponding build scripts, each inheriting from `target_base_image` and using libCRS for artifact submission. The coverage builder uses ARGUS with `BANDFUZZ_PROFILE=1`, the compile_commands builder uses ARGUS with `GENERATE_COMPILATION_DATABASE=1`, and the callgraph builder uses ARGUS with `ADD_ADDITIONAL_PASSES=SeedMindCFPass.so` and `ADD_ADDITIONAL_OBJECTS=libcallgraph_rt.a`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None - user opted for Claude's judgment on all build-target implementation details.

### Claude's Discretion
User opted for Claude's judgment on all build-target implementation details. The following areas are open for research-informed decisions:

**Builder separation strategy:**
- How to structure the three Dockerfiles (coverage, compile_commands, callgraph)
- Whether to share common base layers or keep independent
- Dependency ordering (crs.yaml shows callgraph depends_on coverage)

**Artifact submission approach:**
- How to use libCRS submit-build-output for each builder
- Which directories/files to submit
- Naming conventions for output artifacts

**ARGUS integration:**
- How to invoke ARGUS compiler wrapper for coverage instrumentation
- Environment variable approach (CC/CXX) vs explicit compiler paths
- Coverage flags (-fprofile-instr-generate -fcoverage-mapping)

**Callgraph linkage:**
- How to link libcallgraph_rt.a into harness
- LDFLAGS approach vs linker wrapper
- Integration with SeedMindCFPass.so LLVM pass

### Deferred Ideas (OUT OF SCOPE)
None - user proceeded directly to Claude's judgment
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BLDG-01 | Coverage builder produces instrumented harness with -fprofile-instr-generate | ARGUS ProfileVisitor adds `-fprofile-instr-generate -fcoverage-mapping` when `BANDFUZZ_PROFILE=1` |
| BLDG-02 | compile_commands.json builder extracts compilation database | ARGUS CompilationDatabaseVisitor adds `-MJ` flag when `GENERATE_COMPILATION_DATABASE=1` with `COMPILATION_DATABASE_DIR` |
| BLDG-03 | Call graph builder links harness with libcallgraph_rt | ARGUS AdditionalPassesVisitor adds SeedMindCFPass.so via `-fpass-plugin`, AdditionalObjectsVisitor links libcallgraph_rt.a |
| BLDG-04 | All builders export artifacts via libCRS submit-build-output | buttercup reference shows pattern: `libCRS submit-build-output <local_path> <output_name>` |
</phase_requirements>

## Standard Stack

### Core
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| target_base_image (ARG) | dynamic | Base for all builders; contains OSS-Fuzz target | OSS-CRS pattern - framework provides this |
| libCRS | provided by OSS-CRS | Artifact submission between phases | Required for OSS-CRS integration |
| ARGUS | from prepare phase | Compiler wrapper with visitor-based instrumentation | Already built in seedgen-runtime:latest |
| SeedMindCFPass.so | from prepare phase | LLVM pass for call graph instrumentation | Already built in seedgen-runtime:latest |
| libcallgraph_rt.a | from prepare phase | Runtime library for call graph logging | Already built in seedgen-runtime:latest |

### Supporting
| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| seedgen-runtime:latest | from prepare phase | Source of ARGUS, SeedMindCFPass.so, libcallgraph_rt.a | COPY --from=seedgen-runtime:latest |
| compile command | OSS-Fuzz | Standard build script provided by target | Invoked by all builders |
| llvm-profdata / llvm-cov | base-builder | Coverage data processing tools | Included in coverage builder output |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ARGUS for coverage | Direct clang flags | ARGUS handles edge cases, provides consistent behavior |
| ARGUS for compile_commands | Bear (build recorder) | ARGUS is already installed, simpler integration |
| ARGUS for callgraph | Manual LDFLAGS | ARGUS visitors handle LLVM version-specific pass loading |

**Tools from prepare phase (COPY --from=seedgen-runtime:latest):**
```dockerfile
COPY --from=seedgen-runtime:latest /usr/local/bin/argus /usr/local/bin/argus
COPY --from=seedgen-runtime:latest /usr/local/lib/SeedMindCFPass.so /usr/local/lib/SeedMindCFPass.so
COPY --from=seedgen-runtime:latest /usr/local/lib/libcallgraph_rt.a /usr/local/lib/libcallgraph_rt.a
```

## Architecture Patterns

### Recommended Project Structure
```
oss-crs/
├── crs.yaml                              # Already exists, declares 3 builders
├── docker-bake.hcl                       # Already exists
├── dockerfiles/
│   ├── prepare-base.Dockerfile           # Already exists
│   ├── builder-coverage.Dockerfile       # NEW: Coverage instrumentation
│   ├── builder-compile-commands.Dockerfile  # NEW: Compilation database
│   └── builder-callgraph.Dockerfile      # NEW: Call graph linkage
└── bin/
    ├── builder-coverage.sh               # NEW: Coverage build script
    ├── builder-compile-commands.sh       # NEW: Compile commands script
    └── builder-callgraph.sh              # NEW: Callgraph build script
```

### Pattern 1: Builder Dockerfile Structure
**What:** Minimal Dockerfile that installs libCRS, copies tools from prepare phase, and runs build script
**When to use:** All OSS-CRS builder Dockerfiles
**Example:**
```dockerfile
# Source: buttercup-bugfind/oss-crs/dockerfiles/builder-coverage.Dockerfile
ARG target_base_image
FROM ${target_base_image}

# Install libCRS
COPY --from=libcrs . /opt/libCRS
RUN /opt/libCRS/install.sh

# Copy tools from prepare phase
COPY --from=seedgen-runtime:latest /usr/local/bin/argus /usr/local/bin/argus
COPY --from=seedgen-runtime:latest /usr/local/lib/SeedMindCFPass.so /usr/local/lib/SeedMindCFPass.so
COPY --from=seedgen-runtime:latest /usr/local/lib/libcallgraph_rt.a /usr/local/lib/libcallgraph_rt.a

# Copy build script
COPY oss-crs/bin/builder-coverage.sh /builder.sh
RUN chmod +x /builder.sh

CMD ["/builder.sh"]
```

### Pattern 2: ARGUS Environment Variable Configuration
**What:** Set ARGUS-specific environment variables to enable visitors
**When to use:** Each builder needs different ARGUS behavior
**Example:**
```bash
# Coverage build (BLDG-01)
export BANDFUZZ_PROFILE=1
export CC=/usr/local/bin/argus
export CXX=/usr/local/bin/argus

# Compile commands build (BLDG-02)
export GENERATE_COMPILATION_DATABASE=1
export COMPILATION_DATABASE_DIR=/out/compilation_database
export CC=/usr/local/bin/argus
export CXX=/usr/local/bin/argus

# Callgraph build (BLDG-03)
export ADD_ADDITIONAL_PASSES=SeedMindCFPass.so
export ADD_ADDITIONAL_OBJECTS=/usr/local/lib/libcallgraph_rt.a
export CC=/usr/local/bin/argus
export CXX=/usr/local/bin/argus
```

### Pattern 3: libCRS submit-build-output
**What:** Submit local directory/file to OSS-CRS build output system
**When to use:** End of every builder script
**Example:**
```bash
# Source: buttercup-bugfind builder scripts
# Submit coverage harness
libCRS submit-build-output /artifacts/coverage-harness coverage-harness

# Submit compile_commands.json
libCRS submit-build-output /out/compile_commands compile-commands

# Submit callgraph harness
libCRS submit-build-output /artifacts/callgraph callgraph
```

### Pattern 4: Output Directory Structure
**What:** Organize build outputs for run phase consumption
**When to use:** All builders
**Example:**
```
# Coverage harness output (BLDG-01)
/artifacts/coverage-harness/
├── {harness_name}           # Coverage-instrumented binary
├── llvm-profdata            # For coverage merging
└── llvm-cov                 # For coverage reporting

# Compile commands output (BLDG-02)
/out/compile_commands/
└── compile_commands.json    # Merged compilation database

# Callgraph output (BLDG-03)
/artifacts/callgraph/
└── {harness_name}           # Callgraph-instrumented binary
```

### Anti-Patterns to Avoid
- **Hardcoding harness names:** Use OSS-Fuzz compile output, don't assume specific binary names
- **Mixing build configurations:** Keep coverage, compile_commands, and callgraph as separate builds
- **Skipping artifact verification:** Check outputs exist before calling submit-build-output
- **Missing ARGUS environment variables:** ARGUS visitors only activate when env vars are set

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Coverage instrumentation | Manual clang flags | ARGUS with `BANDFUZZ_PROFILE=1` | ARGUS ProfileVisitor handles edge cases |
| Compilation database | Manual -MJ flags | ARGUS with `GENERATE_COMPILATION_DATABASE=1` | ARGUS creates unique filenames, handles merging input |
| LLVM pass loading | Manual -fpass-plugin | ARGUS with `ADD_ADDITIONAL_PASSES` | ARGUS handles LLVM version differences (1-10 vs 11-15 vs 16+) |
| Static library linkage | Manual LDFLAGS | ARGUS with `ADD_ADDITIONAL_OBJECTS` | ARGUS adds at correct position in link command |
| Compilation database merging | Custom script | SeedD ConstructCompilationDatabase() | Already implemented in seedd, merges individual JSON files |
| Artifact transfer | Custom rsync/copy | libCRS submit-build-output | OSS-CRS framework handles destination routing |

**Key insight:** ARGUS visitors are the recommended approach for all compiler modifications. The visitors handle LLVM version compatibility, flag ordering, and edge cases that manual approaches miss.

## Common Pitfalls

### Pitfall 1: Build Output Path Mismatch
**What goes wrong:** Builder submits artifacts to wrong path, run phase can't find them
**Why it happens:** crs.yaml declares `outputs: [coverage-harness]` but script calls `libCRS submit-build-output /out task`
**How to avoid:** Match submit-build-output destination exactly to crs.yaml outputs list
**Warning signs:** Run phase errors: "build output not found", rsync failures

### Pitfall 2: ARGUS Not Used as CC/CXX
**What goes wrong:** Compile runs but harness has no instrumentation
**Why it happens:** OSS-Fuzz compile script uses system clang, not ARGUS
**How to avoid:** Set `CC=/usr/local/bin/argus` and `CXX=/usr/local/bin/argus` before calling compile
**Warning signs:** Harness runs but no coverage data generated, no call graph output

### Pitfall 3: Missing libcallgraph_rt.a Linkage
**What goes wrong:** Harness compiles but crashes at runtime with undefined symbol
**Why it happens:** SeedMindCFPass.so adds calls to `__seedmind_record_func_call` but runtime not linked
**How to avoid:** Set `ADD_ADDITIONAL_OBJECTS=/usr/local/lib/libcallgraph_rt.a`
**Warning signs:** Runtime error: "undefined symbol: __seedmind_record_func_call"

### Pitfall 4: Compilation Database Directory Not Created
**What goes wrong:** ARGUS silently fails to write compilation database files
**Why it happens:** `COMPILATION_DATABASE_DIR` points to non-existent directory
**How to avoid:** Create directory before build: `mkdir -p /out/compilation_database`
**Warning signs:** Empty /out/compile_commands/compile_commands.json or missing file

### Pitfall 5: Wrong LLVM Tools Version
**What goes wrong:** llvm-profdata or llvm-cov incompatible with instrumented binary
**Why it happens:** Copy tools from different LLVM version than used for compilation
**How to avoid:** Copy llvm-profdata and llvm-cov from target_base_image, not prepare image
**Warning signs:** "unsupported profraw version" or "coverage version mismatch"

### Pitfall 6: Callgraph Builder Without depends_on
**What goes wrong:** Callgraph builder runs before coverage builder, can't reuse source
**Why it happens:** crs.yaml doesn't declare dependency
**How to avoid:** crs.yaml already declares `depends_on: [build-coverage]` - preserve this
**Warning signs:** Inconsistent build results, parallel execution race conditions

## Code Examples

Verified patterns from existing codebase and references:

### Builder Dockerfile (Coverage)
```dockerfile
# Source: Adapted from buttercup-bugfind/oss-crs/dockerfiles/builder-coverage.Dockerfile
ARG target_base_image
FROM ${target_base_image}

# Install libCRS
COPY --from=libcrs . /opt/libCRS
RUN /opt/libCRS/install.sh

# Copy ARGUS from prepare phase
COPY --from=seedgen-runtime:latest /usr/local/bin/argus /usr/local/bin/argus

# Copy build script
COPY oss-crs/bin/builder-coverage.sh /builder.sh
RUN chmod +x /builder.sh

CMD ["/builder.sh"]
```

### Builder Script (Coverage) - BLDG-01
```bash
#!/bin/bash
# Build coverage-instrumented harness using ARGUS ProfileVisitor
set -e

echo "[builder-coverage] Starting coverage build..."

# Configure ARGUS for coverage instrumentation
# ProfileVisitor adds: -fprofile-instr-generate -fcoverage-mapping
export BANDFUZZ_PROFILE=1
export CC=/usr/local/bin/argus
export CXX=/usr/local/bin/argus

# Set coverage sanitizer for OSS-Fuzz
export SANITIZER=coverage

# Clean previous build artifacts
rm -rf /out/* /work/*

# Run OSS-Fuzz compile script
compile

# Prepare output directory
mkdir -p /artifacts/coverage-harness

# Copy harness binaries (all executables except known non-harness files)
for item in /out/*; do
    if [ -f "$item" ] && [ -x "$item" ]; then
        case "$(basename "$item")" in
            *.a|*.o|*.so|*.dict|*.options)
                continue
                ;;
            *)
                cp "$item" /artifacts/coverage-harness/
                ;;
        esac
    fi
done

# Copy LLVM coverage tools from base image
cp /usr/bin/llvm-profdata /artifacts/coverage-harness/ 2>/dev/null || true
cp /usr/bin/llvm-cov /artifacts/coverage-harness/ 2>/dev/null || true

echo "[builder-coverage] Coverage build complete"
ls -la /artifacts/coverage-harness/

# Submit via libCRS
libCRS submit-build-output /artifacts/coverage-harness coverage-harness

echo "[builder-coverage] Submitted coverage-harness"
```

### Builder Script (Compile Commands) - BLDG-02
```bash
#!/bin/bash
# Generate compile_commands.json using ARGUS CompilationDatabaseVisitor
set -e

echo "[builder-compile-commands] Starting compile_commands build..."

# Configure ARGUS for compilation database generation
# CompilationDatabaseVisitor adds: -MJ <dir>/<uuid>.json
export GENERATE_COMPILATION_DATABASE=1
export COMPILATION_DATABASE_DIR=/out/compilation_database
export CC=/usr/local/bin/argus
export CXX=/usr/local/bin/argus

# Create output directory (ARGUS needs this to exist)
mkdir -p "$COMPILATION_DATABASE_DIR"

# Clean previous build artifacts
rm -rf /out/* /work/*
mkdir -p "$COMPILATION_DATABASE_DIR"

# Run OSS-Fuzz compile script
compile

# Merge individual JSON files into compile_commands.json
# The individual files have format: { "directory": "...", "file": "...", "arguments": [...] },
mkdir -p /out/compile_commands

# Create merged compile_commands.json
echo "[" > /out/compile_commands/compile_commands.json
first=true
for f in "$COMPILATION_DATABASE_DIR"/*.json; do
    if [ -f "$f" ]; then
        if [ "$first" = true ]; then
            first=false
        else
            echo "," >> /out/compile_commands/compile_commands.json
        fi
        # Remove trailing comma from each file
        sed 's/,$//' "$f" >> /out/compile_commands/compile_commands.json
    fi
done
echo "]" >> /out/compile_commands/compile_commands.json

echo "[builder-compile-commands] compile_commands.json created"
wc -l /out/compile_commands/compile_commands.json

# Submit via libCRS
libCRS submit-build-output /out/compile_commands compile-commands

echo "[builder-compile-commands] Submitted compile-commands"
```

### Builder Script (Callgraph) - BLDG-03
```bash
#!/bin/bash
# Build callgraph-instrumented harness using ARGUS LLVM pass integration
set -e

echo "[builder-callgraph] Starting callgraph build..."

# Configure ARGUS for callgraph instrumentation
# AdditionalPassesVisitor adds: -fpass-plugin=/usr/local/lib/SeedMindCFPass.so
# AdditionalObjectsVisitor links: libcallgraph_rt.a
export ADD_ADDITIONAL_PASSES=SeedMindCFPass.so
export ADD_ADDITIONAL_OBJECTS=/usr/local/lib/libcallgraph_rt.a
export CC=/usr/local/bin/argus
export CXX=/usr/local/bin/argus

# Use address sanitizer for callgraph build (like coverage builder depends_on)
export SANITIZER=address

# Clean previous build artifacts
rm -rf /out/* /work/*

# Run OSS-Fuzz compile script
compile

# Prepare output directory
mkdir -p /artifacts/callgraph

# Copy harness binaries
for item in /out/*; do
    if [ -f "$item" ] && [ -x "$item" ]; then
        case "$(basename "$item")" in
            *.a|*.o|*.so|*.dict|*.options)
                continue
                ;;
            *)
                cp "$item" /artifacts/callgraph/
                ;;
        esac
    fi
done

echo "[builder-callgraph] Callgraph build complete"
ls -la /artifacts/callgraph/

# Submit via libCRS
libCRS submit-build-output /artifacts/callgraph callgraph

echo "[builder-callgraph] Submitted callgraph"
```

### crs.yaml target_build_phase (already exists)
```yaml
# Source: oss-crs/crs.yaml (current)
target_build_phase:
  - name: build-coverage
    dockerfile: oss-crs/dockerfiles/builder-coverage.Dockerfile
    outputs:
      - coverage-harness

  - name: build-compile-commands
    dockerfile: oss-crs/dockerfiles/builder-compile-commands.Dockerfile
    outputs:
      - compile-commands

  - name: build-callgraph
    dockerfile: oss-crs/dockerfiles/builder-callgraph.Dockerfile
    depends_on:
      - build-coverage
    outputs:
      - callgraph
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Bear for compile_commands | ARGUS CompilationDatabaseVisitor | ARGUS feature | Simpler, no separate tool needed |
| Manual -fpass-plugin | ARGUS AdditionalPassesVisitor | ARGUS feature | Handles LLVM version differences |
| SANITIZER=coverage | BANDFUZZ_PROFILE=1 with ARGUS | ARGUS ProfileVisitor | More consistent flag handling |
| Single build output | Multiple parallel/sequential builders | OSS-CRS design | Coverage, compile_commands, callgraph separate |

**Current ecosystem:**
- OSS-CRS: Multi-builder pattern with depends_on for ordering
- ARGUS: Visitor-based compiler wrapper for all instrumentation
- libCRS: Standard artifact submission via submit-build-output

## Open Questions

1. **SeedMindCFPass.so LLVM Version Compatibility**
   - What we know: build.sh uses `llvm-config --cxxflags` from base-builder
   - What's unclear: Will it work with all OSS-Fuzz target base images?
   - Recommendation: Test with representative targets; the pass was built against base-builder's LLVM

2. **Coverage Build vs Callgraph Build Harness**
   - What we know: Run phase needs both coverage feedback and call graph data
   - What's unclear: Does run phase need both binaries, or just one with both instrumentations?
   - Recommendation: Keep separate; coverage binary for GetCov, callgraph binary for GetCallGraph

3. **Compile Commands Merging**
   - What we know: ARGUS writes individual JSON files, seedd has ConstructCompilationDatabase() for merging
   - What's unclear: Should builder do the merge, or let run phase do it?
   - Recommendation: Builder does merge - simpler for run phase to consume a single file

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Docker build + oss-crs build-target command |
| Config file | oss-crs/crs.yaml |
| Quick run command | `docker buildx bake -f oss-crs/docker-bake.hcl --print` (validate prepare) |
| Full suite command | `oss-crs build-target` with a test target |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BLDG-01 | Coverage harness has profiling instrumentation | integration | Build test target, run with LLVM_PROFILE_FILE, verify .profraw generated | Wave 0 |
| BLDG-02 | compile_commands.json created with entries | smoke | Check file exists and is valid JSON array | Wave 0 |
| BLDG-03 | Callgraph harness linked with libcallgraph_rt | integration | Run with EXPORT_CALLS=1, verify /tmp/callgraph.log created | Wave 0 |
| BLDG-04 | All outputs submitted via libCRS | integration | `oss-crs build-target` completes without errors | Wave 0 |

### Sampling Rate
- **Per task commit:** Dockerfile syntax check, script shellcheck
- **Per wave merge:** `docker build` for each builder Dockerfile
- **Phase gate:** `oss-crs build-target` with CRSBench or freerdp target succeeds

### Wave 0 Gaps
- [ ] `oss-crs/dockerfiles/builder-coverage.Dockerfile` - coverage builder
- [ ] `oss-crs/dockerfiles/builder-compile-commands.Dockerfile` - compile_commands builder
- [ ] `oss-crs/dockerfiles/builder-callgraph.Dockerfile` - callgraph builder
- [ ] `oss-crs/bin/builder-coverage.sh` - coverage build script
- [ ] `oss-crs/bin/builder-compile-commands.sh` - compile_commands script
- [ ] `oss-crs/bin/builder-callgraph.sh` - callgraph build script

## Sources

### Primary (HIGH confidence)
- `components/seedgen/argus/README.md` - ARGUS visitor documentation and environment variables
- `components/seedgen/argus/src/option_visitors/*.rs` - Actual visitor implementations
- `components/seedgen/callgraph/llvm/SeedMindCFPass.cpp` - LLVM pass implementation
- `components/seedgen/callgraph/runtime/src/lib.rs` - Runtime library exports
- `oss-crs/crs.yaml` - Current project crs.yaml with builder declarations
- `oss-crs/dockerfiles/prepare-base.Dockerfile` - Prepare phase patterns

### Secondary (MEDIUM confidence)
- `/home/andrew/post/buttercup-bugfind/oss-crs/dockerfiles/builder*.Dockerfile` - Reference implementations
- `/home/andrew/post/buttercup-bugfind/oss-crs/bin/builder*.sh` - Reference build scripts
- `.planning/research/ARCHITECTURE.md` - OSS-CRS architecture patterns
- `.planning/research/PITFALLS.md` - Known pitfalls for build-target phase

### Tertiary (LOW confidence)
- None - all critical patterns verified from existing code and references

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Tools already built in prepare phase, proven patterns from buttercup
- Architecture: HIGH - crs.yaml already declares correct builder structure
- Pitfalls: HIGH - ARGUS environment variables documented in README, libCRS patterns from references

**Research date:** 2026-03-12
**Valid until:** 2026-04-12 (stable domain; ARGUS visitors well-documented)
