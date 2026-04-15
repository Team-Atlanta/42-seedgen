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

# Copy LLVM coverage tools from base image (search common paths)
for tool in llvm-profdata llvm-cov; do
    for path in /usr/bin /usr/local/bin /usr/lib/llvm-*/bin; do
        if [ -x "${path}/${tool}" ]; then
            cp "${path}/${tool}" /artifacts/coverage-harness/
            echo "[builder-coverage] Copied ${tool} from ${path}"
            break
        fi
    done
done

echo "[builder-coverage] Coverage build complete"
ls -la /artifacts/coverage-harness/

# Submit via libCRS
libCRS submit-build-output /artifacts/coverage-harness coverage-harness
echo "[builder-coverage] Submitted coverage-harness"

# Capture post-build source tree for SeedD source serving
# LLVM coverage data references absolute paths as they existed during compilation
libCRS submit-build-output /src source-tree
echo "[builder-coverage] Submitted source-tree"
