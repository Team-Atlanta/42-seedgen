# Unified builder Dockerfile
# Single compile with coverage + callgraph + compile_commands instrumentation
ARG target_base_image
FROM ${target_base_image}

# Install libCRS for artifact submission
COPY --from=libcrs . /opt/libCRS
RUN /opt/libCRS/install.sh

# Copy ARGUS compiler wrapper from prepare phase
COPY --from=seedgen-runtime:latest /usr/local/bin/argus /usr/local/bin/argus

# Build LLVM pass and copy callgraph runtime (C/C++ targets only)
# Skipped gracefully on JVM targets where llvm-config is unavailable
COPY components/seedgen/callgraph/llvm /tmp/llvm-pass
RUN cd /tmp/llvm-pass && (./build.sh && cp SeedMindCFPass.so /SeedMindCFPass.so || echo "LLVM pass build skipped (no llvm-config)") && rm -rf /tmp/llvm-pass
COPY --from=seedgen-runtime:latest /usr/local/lib/libcallgraph_rt.a /libcallgraph_rt.a

# Copy build script
COPY oss-crs/bin/builder.sh /builder.sh
RUN chmod +x /builder.sh

CMD ["/builder.sh"]
