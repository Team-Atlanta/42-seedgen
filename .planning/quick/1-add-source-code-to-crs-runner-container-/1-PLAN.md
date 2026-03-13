---
phase: quick-1
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - oss-crs/bin/runner.py
autonomous: true
requirements: [QUICK-1]
must_haves:
  truths:
    - "SeedD can serve source code via GetRegionSource and ExtractFunctionSource"
    - "Source files exist in container before SeedD starts"
  artifacts:
    - path: "oss-crs/bin/runner.py"
      provides: "Source download before SeedD startup"
      contains: "download-source"
  key_links:
    - from: "runner.py download_source()"
      to: "libCRS download-source"
      via: "subprocess.run"
      pattern: "download-source.*target.*/src"
---

<objective>
Add source code download to CRS runner container so SeedD can serve source files.

Purpose: SeedD gRPC methods (GetRegionSource, ExtractFunctionSource) need access to source files referenced in compile_commands.json. Currently only build artifacts are downloaded, not the actual source code.

Output: Modified runner.py that downloads source before starting SeedD.
</objective>

<execution_context>
@/home/andrew/.claude/get-shit-done/workflows/execute-plan.md
@/home/andrew/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@oss-crs/bin/runner.py

The libCRS CLI provides `download-source <type> <dst_path>` where:
- type: `target` (uses OSS_CRS_PROJ_PATH env var for pre-build source)
- dst_path: destination directory (typically /src)

SeedD expects source at paths matching compile_commands.json entries. The /src path is the standard location used by OSS-CRS for target project source.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add download_source function and integrate into runner</name>
  <files>oss-crs/bin/runner.py</files>
  <action>
Add a new `download_source()` function after `download_artifacts()` that:
1. Calls `libCRS download-source target /src` via subprocess.run
2. Logs download start/complete events using log_json pattern
3. Raises RuntimeError on failure (matching existing error handling)
4. Verifies /src directory exists after download

In main():
1. Call download_source() AFTER download_artifacts() but BEFORE setup_seedd_artifacts()
2. Wrap in try/except with log_json("fatal_error", stage="download_source", ...) and sys.exit(1)

The source must be available before SeedD starts since SeedD reads paths from compile_commands.json which reference source file locations.

Pattern to follow from existing download_artifacts():
```python
def download_source():
    """Download target project source code via libCRS."""
    log_json("download_source_start")

    result = subprocess.run(
        ["libCRS", "download-source", "target", "/src"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        log_json("download_source_failed", error=result.stderr)
        raise RuntimeError(f"Failed to download source: {result.stderr}")

    if not os.path.isdir("/src"):
        log_json("source_dir_missing", path="/src")
        raise RuntimeError("Source downloaded but /src directory not found")

    log_json("download_source_complete", path="/src")
```
  </action>
  <verify>
    <automated>grep -q "download-source.*target.*/src" oss-crs/bin/runner.py && grep -q "download_source()" oss-crs/bin/runner.py && echo "PASS"</automated>
  </verify>
  <done>runner.py downloads source code via libCRS before SeedD startup; function follows existing error handling and logging patterns</done>
</task>

</tasks>

<verification>
- runner.py contains download_source function
- download_source is called in main() after download_artifacts but before setup_seedd_artifacts
- Error handling matches existing pattern (try/except with fatal_error log)
</verification>

<success_criteria>
- Source download integrated into runner startup sequence
- SeedD will have access to /src when it starts
- Code follows existing project patterns for subprocess calls and logging
</success_criteria>

<output>
After completion, create `.planning/quick/1-add-source-code-to-crs-runner-container-/1-SUMMARY.md`
</output>
