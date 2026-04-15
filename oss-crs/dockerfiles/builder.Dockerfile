# Unified builder Dockerfile
# Single compile with coverage + callgraph + compile_commands instrumentation
ARG target_base_image
FROM ${target_base_image}

# Install libCRS for artifact submission
COPY --from=libcrs . /opt/libCRS
RUN /opt/libCRS/install.sh

# Copy ARGUS compiler wrapper from prepare phase
COPY --from=seedgen-runtime:latest /usr/local/bin/argus /usr/local/bin/argus

# Copy LLVM pass and runtime library for callgraph instrumentation
COPY --from=seedgen-runtime:latest /usr/local/lib/SeedMindCFPass.so /usr/local/lib/SeedMindCFPass.so
COPY --from=seedgen-runtime:latest /usr/local/lib/libcallgraph_rt.a /usr/local/lib/libcallgraph_rt.a

# Copy build script
COPY oss-crs/bin/builder.sh /builder.sh
RUN chmod +x /builder.sh

CMD ["/builder.sh"]
