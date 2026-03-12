# Phase 2: Build-Target - Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Create build-target phase Dockerfiles that instrument the target harness and produce artifacts for the run phase. Three builders: coverage-instrumented harness, compile_commands.json, and call graph linkage. Success: `oss-crs build-target` completes and all artifacts are submitted via libCRS.

</domain>

<decisions>
## Implementation Decisions

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

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `oss-crs/dockerfiles/prepare-base.Dockerfile`: Multi-stage Dockerfile pattern from Phase 1
- `seedgen-runtime:latest`: Prepare-phase image with all tools installed
- `oss-crs/crs.yaml`: Already declares the three builders with outputs

### Established Patterns
- `COPY --from=seedgen-runtime:latest`: Pull tools from prepare image
- libCRS submit-build-output: Standard OSS-CRS artifact submission
- buttercup-bugfind patterns for builder Dockerfiles

### Integration Points
- Builders receive OSS-Fuzz target via build context
- Outputs consumed by runner in Phase 3
- libCRS handles artifact transfer between phases

</code_context>

<specifics>
## Specific Ideas

- Reference buttercup-bugfind builder Dockerfiles for libCRS integration patterns
- Use OSS-Fuzz compile.sh script as entrypoint (standard OSS-Fuzz target build flow)
- Follow established ARGUS usage from existing seedgen codebase

</specifics>

<deferred>
## Deferred Ideas

None — user proceeded directly to Claude's judgment

</deferred>

---

*Phase: 02-build-target*
*Context gathered: 2026-03-12*
