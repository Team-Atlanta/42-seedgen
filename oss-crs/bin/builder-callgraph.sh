#!/bin/bash
# Build callgraph-instrumented harness using ARGUS LLVM pass integration
set -e

echo "[builder-callgraph] Starting callgraph build..."

# Configure ARGUS for callgraph instrumentation
# AdditionalPassesVisitor adds: -fpass-plugin=/usr/local/lib/SeedMindCFPass.so
# AdditionalObjectsVisitor links: libcallgraph_rt.a
export ADD_ADDITIONAL_PASSES=SeedMindCFPass.so
export ADD_ADDITIONAL_OBJECTS=/usr/local/lib/libcallgraph_rt.a
export CC=/usr/local/bin/argus
export CXX=/usr/local/bin/argus

# Use address sanitizer for callgraph build (per research recommendation)
export SANITIZER=address

# Clean previous build artifacts
rm -rf /out/* /work/*

# Run OSS-Fuzz compile script
compile

# Prepare output directory
mkdir -p /artifacts/callgraph

# Copy harness binaries (all executables except known non-harness files)
for item in /out/*; do
    if [ -f "$item" ] && [ -x "$item" ]; then
        case "$(basename "$item")" in
            *.a|*.o|*.so|*.dict|*.options)
                continue
                ;;
            *)
                cp "$item" /artifacts/callgraph/
                ;;
        esac
    fi
done

echo "[builder-callgraph] Callgraph build complete"
ls -la /artifacts/callgraph/

# Submit via libCRS
libCRS submit-build-output /artifacts/callgraph callgraph

echo "[builder-callgraph] Submitted callgraph"
