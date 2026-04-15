#!/bin/bash
# Unified builder: produces harness binaries with coverage + callgraph instrumentation,
# plus compile_commands.json and post-build source tree.
# Single compile invocation matching the original 42-afc-crs approach.
set -e

echo "[builder] Starting unified build..."

# Configure ARGUS for all instrumentations in one compile:
# - ProfileVisitor: -fprofile-instr-generate -fcoverage-mapping (coverage)
# - AdditionalPassesVisitor: -fpass-plugin=SeedMindCFPass.so (callgraph LLVM pass)
# - RuntimeVisitor: links libcallgraph_rt.a + -lpthread -ldl -lgcc (callgraph runtime)
# - CompilationDatabaseVisitor: -MJ <dir>/<uuid>.json (compile commands)
export CC=/usr/local/bin/argus
export CXX=/usr/local/bin/argus
export BANDFUZZ_PROFILE=1
export BANDFUZZ_OPT=0
export ADD_ADDITIONAL_PASSES=SeedMindCFPass.so
export ADD_RUNTIME=1
export BANDFUZZ_RUNTIME=libcallgraph_rt.a
export GENERATE_COMPILATION_DATABASE=1
export COMPILATION_DATABASE_DIR=/out/compilation_database

# Create output directory for compilation database (ARGUS needs this to exist)
mkdir -p "$COMPILATION_DATABASE_DIR"

# Clean previous build artifacts
rm -rf /out/* /work/*
mkdir -p "$COMPILATION_DATABASE_DIR"

# Single compile with all instrumentations
compile

# --- Submit harness binaries (coverage + callgraph instrumented) ---
mkdir -p /artifacts/harness

for item in /out/*; do
    if [ -f "$item" ] && [ -x "$item" ]; then
        case "$(basename "$item")" in
            *.a|*.o|*.so|*.dict|*.options)
                continue
                ;;
            *)
                cp "$item" /artifacts/harness/
                ;;
        esac
    fi
done

# Copy LLVM coverage tools from base image
for tool in llvm-profdata llvm-cov llvm-symbolizer; do
    for path in /usr/bin /usr/local/bin /usr/lib/llvm-*/bin; do
        if [ -x "${path}/${tool}" ]; then
            cp "${path}/${tool}" /artifacts/harness/
            echo "[builder] Copied ${tool} from ${path}"
            break
        fi
    done
done

echo "[builder] Harness build complete"
ls -la /artifacts/harness/

libCRS submit-build-output /artifacts/harness harness
echo "[builder] Submitted harness"

# --- Submit compile_commands.json ---
mkdir -p /out/compile_commands

echo "[" > /out/compile_commands/compile_commands.json
first=true
for f in "$COMPILATION_DATABASE_DIR"/*.json; do
    if [ -f "$f" ]; then
        if [ "$first" = true ]; then
            first=false
        else
            echo "," >> /out/compile_commands/compile_commands.json
        fi
        sed 's/,$//' "$f" >> /out/compile_commands/compile_commands.json
    fi
done
echo "]" >> /out/compile_commands/compile_commands.json

echo "[builder] compile_commands.json created"
wc -l /out/compile_commands/compile_commands.json

libCRS submit-build-output /out/compile_commands compile-commands
echo "[builder] Submitted compile-commands"

# --- Submit post-build source tree ---
libCRS submit-build-output /src source-tree
echo "[builder] Submitted source-tree"
