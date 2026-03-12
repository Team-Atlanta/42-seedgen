# Phase 1: Prepare - Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Create OSS-CRS repository structure and build prepare-phase images. Success: `oss-crs prepare` completes and images contain ARGUS, GetCov, SeedD, and libcallgraph_rt.

</domain>

<decisions>
## Implementation Decisions

### Tool Build Approach
- Use separate HCL targets in docker-bake.hcl for each tool
- Benefits: Better build caching, modular rebuilds, clearer dependency graph
- Each tool (ARGUS, GetCov, SeedD, libcallgraph_rt) gets its own build target

### LLVM Version
- Match whatever LLVM version OSS-Fuzz base images use
- Don't pin to specific version — maintain compatibility with OSS-Fuzz ecosystem
- Check OSS-Fuzz base image for current LLVM version at build time

### Image Organization
- Single combined runtime image containing all tools
- Simpler for build-target and run phases to use
- HCL targets produce intermediate images, final target combines them

### Directory Layout
- Follow buttercup pattern: `oss-crs/` subdirectory for all OSS-CRS files
- Structure: `oss-crs/crs.yaml`, `oss-crs/docker-bake.hcl`, `oss-crs/dockerfiles/`

### Claude's Discretion
- Exact Dockerfile structure and build stages
- HCL target naming conventions
- Base image selection (Ubuntu vs Alpine vs Debian)
- Build optimization (parallel stages, layer caching)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `components/seedgen/argus/`: ARGUS compiler wrapper source
- `components/seedgen/getcov/`: GetCov coverage tool source
- `components/seedgen/seedd/`: SeedD gRPC service source (Go)
- `components/seedgen/callgraph/`: libcallgraph_rt source

### Established Patterns
- Buttercup reference: `~/post/buttercup-bugfind/oss-crs/` for HCL and Dockerfile patterns
- OSS-CRS libCRS: Standard for artifact submission/download

### Integration Points
- docker-bake.hcl produces images tagged for use in build-target phase
- Build-target Dockerfiles will `COPY --from=` prepare images

</code_context>

<specifics>
## Specific Ideas

- Reference buttercup-bugfind for HCL structure and patterns
- Reference crs-libfuzzer for simpler examples
- Use OSS-Fuzz base image LLVM for compatibility

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-prepare*
*Context gathered: 2026-03-12*
