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

# Copy LLVM coverage tools from base image
cp /usr/bin/llvm-profdata /artifacts/coverage-harness/ 2>/dev/null || true
cp /usr/bin/llvm-cov /artifacts/coverage-harness/ 2>/dev/null || true

echo "[builder-coverage] Coverage build complete"
ls -la /artifacts/coverage-harness/

# Submit via libCRS
libCRS submit-build-output /artifacts/coverage-harness coverage-harness

echo "[builder-coverage] Submitted coverage-harness"
