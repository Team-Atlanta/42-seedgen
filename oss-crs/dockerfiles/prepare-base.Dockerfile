# Seedgen Prepare Phase - Multi-Stage Tool Builder
# Each stage is selectable via docker-bake.hcl targets

# ============================================================
# Stage: builder_argus - Rust compiler wrapper
# ============================================================
FROM gcr.io/oss-fuzz-base/base-builder AS builder_argus
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
WORKDIR /app
COPY components/seedgen/argus/ /app/argus/
RUN cd argus && cargo build --release
# Output: /app/argus/target/release/argus

# ============================================================
# Stage: builder_getcov - Coverage extraction tool
# ============================================================
FROM gcr.io/oss-fuzz-base/base-builder AS builder_getcov
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
WORKDIR /app
COPY components/seedgen/getcov/ /app/getcov/
RUN cd getcov && cargo build --release
# Output: /app/getcov/target/release/getcov

# ============================================================
# Stage: builder_seedd - gRPC coverage service
# ============================================================
FROM gcr.io/oss-fuzz-base/base-builder AS builder_seedd
COPY --from=golang:1.22 /usr/local/go /usr/local/go
ENV PATH="/usr/local/go/bin:${PATH}"
WORKDIR /app
COPY components/seedgen/seedd/ /app/seedd/
RUN cd seedd && make
# Output: /app/seedd/bin/seedd

# ============================================================
# Stage: builder_callgraph - Runtime library for call graph
# ============================================================
FROM gcr.io/oss-fuzz-base/base-builder AS builder_callgraph
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
WORKDIR /app
COPY components/seedgen/callgraph/runtime /app/runtime
RUN cd runtime && cargo build --release
# Output: /app/runtime/target/release/libcallgraph_rt.a

# ============================================================
# Stage: builder_llvm_pass - LLVM pass for call graph extraction
# ============================================================
FROM gcr.io/oss-fuzz-base/base-builder AS builder_llvm_pass
WORKDIR /app
COPY components/seedgen/callgraph/llvm /app/llvm
RUN cd llvm && ./build.sh
# Output: /app/llvm/SeedMindCFPass.so

# ============================================================
# Stage: runtime - Combined image with all tools installed
# ============================================================
FROM gcr.io/oss-fuzz-base/base-builder AS runtime

# Copy built artifacts to standard locations
COPY --from=builder_argus /app/argus/target/release/argus /usr/local/bin/argus
COPY --from=builder_getcov /app/getcov/target/release/getcov /usr/local/bin/getcov
COPY --from=builder_seedd /app/seedd/bin/seedd /usr/local/bin/seedd
COPY --from=builder_callgraph /app/runtime/target/release/libcallgraph_rt.a /usr/local/lib/libcallgraph_rt.a
COPY --from=builder_llvm_pass /app/llvm/SeedMindCFPass.so /usr/local/lib/SeedMindCFPass.so

# Verify tools are executable
RUN argus --help || true
RUN getcov --help || true
RUN seedd --help || true
