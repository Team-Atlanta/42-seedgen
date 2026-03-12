#!/bin/bash
# Mock coverage harness for testing validation scripts
# Simulates coverage-harness binary behavior:
# - Accepts input from stdin (like real harness)
# - Generates default.profraw file (for llvm-profdata to find)
# - Exits cleanly

# Read stdin to simulate processing input
while IFS= read -r line; do
  : # consume stdin silently
done

# Create mock profraw file
# Real profraw files contain LLVM profile data, but for fixture testing
# we only need the file to exist - validation scripts use pre-generated JSON
echo "mock profraw data" > default.profraw

# Exit successfully
exit 0
