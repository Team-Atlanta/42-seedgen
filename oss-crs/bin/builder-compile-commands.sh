#!/bin/bash
# Generate compile_commands.json using ARGUS CompilationDatabaseVisitor
set -e

echo "[builder-compile-commands] Starting compile_commands build..."

# Configure ARGUS for compilation database generation
# CompilationDatabaseVisitor adds: -MJ <dir>/<uuid>.json
export GENERATE_COMPILATION_DATABASE=1
export COMPILATION_DATABASE_DIR=/out/compilation_database
export CC=/usr/local/bin/argus
export CXX=/usr/local/bin/argus

# Create output directory (ARGUS needs this to exist)
mkdir -p "$COMPILATION_DATABASE_DIR"

# Clean previous build artifacts
rm -rf /out/* /work/*
mkdir -p "$COMPILATION_DATABASE_DIR"

# Run OSS-Fuzz compile script
compile

# Merge individual JSON files into compile_commands.json
# The individual files have format: { "directory": "...", "file": "...", "arguments": [...] },
mkdir -p /out/compile_commands

# Create merged compile_commands.json
echo "[" > /out/compile_commands/compile_commands.json
first=true
for f in "$COMPILATION_DATABASE_DIR"/*.json; do
    if [ -f "$f" ]; then
        if [ "$first" = true ]; then
            first=false
        else
            echo "," >> /out/compile_commands/compile_commands.json
        fi
        # Remove trailing comma from each file
        sed 's/,$//' "$f" >> /out/compile_commands/compile_commands.json
    fi
done
echo "]" >> /out/compile_commands/compile_commands.json

echo "[builder-compile-commands] compile_commands.json created"
wc -l /out/compile_commands/compile_commands.json

# Submit via libCRS
libCRS submit-build-output /out/compile_commands compile-commands

echo "[builder-compile-commands] Submitted compile-commands"
