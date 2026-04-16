# Unified builder Dockerfile
# Single compile with coverage + callgraph + compile_commands instrumentation
ARG target_base_image
FROM ${target_base_image}

# Install libCRS for artifact submission
COPY --from=libcrs . /opt/libCRS
RUN /opt/libCRS/install.sh

# Copy ARGUS compiler wrapper from prepare phase
COPY --from=seedgen-runtime:latest /usr/local/bin/argus /usr/local/bin/argus

# Build LLVM pass from source against the target's LLVM version
# The pass plugin API version must match the target's clang exactly
COPY components/seedgen/callgraph/llvm /tmp/llvm-pass
RUN cd /tmp/llvm-pass && ./build.sh && cp SeedMindCFPass.so /SeedMindCFPass.so && rm -rf /tmp/llvm-pass

# Copy pre-built callgraph runtime library (Rust, no LLVM version dependency)
COPY --from=seedgen-runtime:latest /usr/local/lib/libcallgraph_rt.a /libcallgraph_rt.a

# Copy build script
COPY oss-crs/bin/builder.sh /builder.sh
RUN chmod +x /builder.sh

CMD ["/builder.sh"]
