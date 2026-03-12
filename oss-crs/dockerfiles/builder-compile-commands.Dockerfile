# Compile commands builder Dockerfile
# Generates compile_commands.json using ARGUS CompilationDatabaseVisitor
ARG target_base_image
FROM ${target_base_image}

# Install libCRS for artifact submission
COPY --from=libcrs . /opt/libCRS
RUN /opt/libCRS/install.sh

# Copy ARGUS from prepare phase
COPY --from=seedgen-runtime:latest /usr/local/bin/argus /usr/local/bin/argus

# Copy build script
COPY oss-crs/bin/builder-compile-commands.sh /builder.sh
RUN chmod +x /builder.sh

CMD ["/builder.sh"]
