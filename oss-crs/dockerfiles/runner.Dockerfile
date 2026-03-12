# Runner Dockerfile
# Downloads build artifacts, starts SeedD, orchestrates seedgen pipeline
ARG seedgen2_src=components/seedgen/seedgen2
FROM seedgen-runtime:latest AS base

# Install libCRS for artifact management (provided by OSS-CRS at build time)
COPY --from=libcrs . /opt/libCRS
RUN /opt/libCRS/install.sh

# Install Python dependencies for seedgen2
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \
    langchain-openai \
    langchain-mcp-adapters \
    langgraph \
    python-dotenv \
    networkx \
    matplotlib \
    jsonschema \
    grpcio \
    grpcio-health-checking

# Copy seedgen2 package
ARG seedgen2_src
COPY ${seedgen2_src} /runner/seedgen2

# Copy runner orchestration script
COPY oss-crs/bin/runner.py /runner/runner.py

# Create working directories
RUN mkdir -p \
    /runner/artifacts \
    /runner/shared \
    /runner/seeds-in \
    /runner/seeds-out

WORKDIR /runner

CMD ["python3", "runner.py"]
