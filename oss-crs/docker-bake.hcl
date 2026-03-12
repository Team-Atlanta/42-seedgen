# Seedgen Prepare Phase - Docker Bake Configuration
# Each tool has its own target for better build caching and modular rebuilds

group "default" {
  targets = ["seedgen-runtime"]
}

# Individual tool builder targets - select named stages from prepare-base.Dockerfile
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

target "builder-seedd" {
  context    = "."
  dockerfile = "oss-crs/dockerfiles/prepare-base.Dockerfile"
  target     = "builder_seedd"
}

target "builder-callgraph" {
  context    = "."
  dockerfile = "oss-crs/dockerfiles/prepare-base.Dockerfile"
  target     = "builder_callgraph"
}

target "builder-llvm-pass" {
  context    = "."
  dockerfile = "oss-crs/dockerfiles/prepare-base.Dockerfile"
  target     = "builder_llvm_pass"
}

# Combined runtime image - the final output of prepare phase
target "seedgen-runtime" {
  context    = "."
  dockerfile = "oss-crs/dockerfiles/prepare-base.Dockerfile"
  target     = "runtime"
  tags       = ["seedgen-runtime:latest"]
}

# Runner image - run phase container
target "runner" {
  context    = "."
  dockerfile = "oss-crs/dockerfiles/runner.Dockerfile"
  contexts = {
    seedgen-runtime = "target:seedgen-runtime"
  }
  tags = ["seedgen-runner:latest"]
}
