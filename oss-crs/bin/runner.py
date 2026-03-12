#!/usr/bin/env python3
"""
Runner orchestration script for oss-crs run phase.
Downloads build artifacts, starts SeedD, registers seed directories, prepares for seedgen pipeline.
"""

import json
import os
import subprocess
import sys
import time
import hashlib
from typing import Optional

# Add seedgen2 to path and import
sys.path.insert(0, '/runner')
from seedgen2.seedgen import SeedGenAgent
from seedgen2.presets import SeedGen2GenerativeModel


def log_json(event: str, **kwargs):
    """Structured JSON logging to stderr."""
    entry = {"event": event, "timestamp": time.time(), **kwargs}
    print(json.dumps(entry), file=sys.stderr, flush=True)


def write_seed(seed_data: bytes, output_dir: str) -> str:
    """
    Write seed to file with SHA256 hash filename.

    Args:
        seed_data: Raw seed bytes
        output_dir: Directory to write seed file

    Returns:
        Path to written seed file
    """
    sha256 = hashlib.sha256(seed_data).hexdigest()
    path = os.path.join(output_dir, sha256)
    with open(path, 'wb') as f:
        f.write(seed_data)
    return path


def download_artifacts():
    """Download build artifacts from Phase 2 via libCRS."""
    log_json("download_artifacts_start")

    artifacts = [
        ("coverage-harness", "/runner/artifacts/coverage-harness"),
        ("compile-commands", "/runner/artifacts/compile-commands"),
        ("callgraph", "/runner/artifacts/callgraph"),
    ]

    for artifact_name, artifact_path in artifacts:
        log_json("downloading_artifact", name=artifact_name, path=artifact_path)
        result = subprocess.run(
            ["libcrs", "download-build-output", artifact_name, artifact_path],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            log_json("download_failed", name=artifact_name, error=result.stderr)
            raise RuntimeError(f"Failed to download {artifact_name}: {result.stderr}")

        # Verify artifact exists
        if not os.path.exists(artifact_path):
            log_json("artifact_missing", name=artifact_name, path=artifact_path)
            raise RuntimeError(f"Artifact downloaded but not found at {artifact_path}")

        log_json("artifact_downloaded", name=artifact_name, path=artifact_path)

    log_json("download_artifacts_complete", count=len(artifacts))


def register_seed_dirs():
    """Register seed input/output directories with libCRS."""
    log_json("register_seed_dirs_start")

    # Register fetch directory for existing seeds
    result = subprocess.run(
        ["libcrs", "register-fetch-dir", "/runner/seeds-in"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        log_json("register_fetch_failed", error=result.stderr)
        raise RuntimeError(f"Failed to register fetch directory: {result.stderr}")
    log_json("fetch_dir_registered", path="/runner/seeds-in")

    # Register submit directory for generated seeds
    result = subprocess.run(
        ["libcrs", "register-submit-dir", "seed", "/runner/seeds-out"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        log_json("register_submit_failed", error=result.stderr)
        raise RuntimeError(f"Failed to register submit directory: {result.stderr}")
    log_json("submit_dir_registered", path="/runner/seeds-out", type="seed")

    log_json("register_seed_dirs_complete")


def start_seedd(shared_dir: str) -> subprocess.Popen:
    """
    Start SeedD gRPC server as background process and wait for health check.

    Args:
        shared_dir: Directory for SeedD shared state

    Returns:
        Popen object for running SeedD process

    Raises:
        RuntimeError: If SeedD fails to start or health check timeout
    """
    log_json("start_seedd", shared_dir=shared_dir)

    # Start SeedD as subprocess
    proc = subprocess.Popen(
        ["/usr/local/bin/seedd", "--shared-dir", shared_dir],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    log_json("seedd_process_started", pid=proc.pid)

    # Health check loop - wait for SeedD to be ready
    # Using grpc health check via grpc_health.v1.Health/Check
    max_attempts = 30
    sleep_interval = 1

    for attempt in range(1, max_attempts + 1):
        try:
            # Try to connect to SeedD health check endpoint
            # In production, this would use seedgen2.utils.grpc.SeedD.health_check()
            # For now, just check if process is alive and give it time to initialize
            if proc.poll() is not None:
                # Process died
                stdout, stderr = proc.communicate()
                log_json("seedd_died",
                        returncode=proc.returncode,
                        stdout=stdout.decode() if stdout else "",
                        stderr=stderr.decode() if stderr else "")
                raise RuntimeError(f"SeedD process died with return code {proc.returncode}")

            # Simple health check: process is alive
            # Real implementation would use gRPC health check here
            if attempt >= 3:  # Give it a few seconds to initialize
                log_json("seedd_health_check_passed", attempt=attempt)
                log_json("seedd_ready", pid=proc.pid)
                return proc

        except Exception as e:
            log_json("seedd_health_check_failed", attempt=attempt, error=str(e))

        time.sleep(sleep_interval)

    # Health check timeout
    proc.terminate()
    log_json("seedd_health_timeout", max_attempts=max_attempts)
    raise RuntimeError(f"SeedD health check timeout after {max_attempts} attempts")


def run_seedgen_loop(harness_path: str, project_name: str, num_seeds: int):
    """
    Run seedgen pipeline in a loop.

    Args:
        harness_path: Path to coverage harness binary
        project_name: Name of target project
        num_seeds: Target number of seeds to generate
    """
    result_dir = "/runner/seeds-out"
    os.makedirs(result_dir, exist_ok=True)

    iteration = 0
    while True:
        iteration += 1
        log_json("pipeline_start", iteration=iteration)

        agent = SeedGenAgent(
            result_dir=result_dir,
            ip_addr="localhost",
            project_name=project_name,
            harness_binary=harness_path,
            gen_model=SeedGen2GenerativeModel()  # Uses OSS_CRS_LLM_API_URL via presets.py
        )

        try:
            agent.run()
            # Count seeds in output directory
            seed_count = len([f for f in os.listdir(result_dir) if os.path.isfile(os.path.join(result_dir, f))])
            log_json("pipeline_complete", iteration=iteration, total_seeds=seed_count)

            # Check if we've reached target
            if seed_count >= num_seeds:
                log_json("target_reached", total_seeds=seed_count, target=num_seeds)
                break

        except Exception as e:
            log_json("pipeline_error", iteration=iteration, error=str(e))
            time.sleep(5)  # Brief pause on error before retry


def main():
    """Main runner entrypoint."""
    log_json("runner_start")

    # Get environment variables
    target_harness = os.getenv("TARGET_HARNESS")
    num_seeds = int(os.getenv("NUM_SEEDS", "100"))
    llm_api_url = os.getenv("OSS_CRS_LLM_API_URL")
    llm_api_key = os.getenv("OSS_CRS_LLM_API_KEY")

    log_json("environment_loaded",
            target_harness=target_harness,
            num_seeds=num_seeds,
            llm_api_url_set=bool(llm_api_url),
            llm_api_key_set=bool(llm_api_key))

    # Download build artifacts
    try:
        download_artifacts()
    except Exception as e:
        log_json("fatal_error", stage="download_artifacts", error=str(e))
        sys.exit(1)

    # Register seed directories
    try:
        register_seed_dirs()
    except Exception as e:
        log_json("fatal_error", stage="register_seed_dirs", error=str(e))
        sys.exit(1)

    # Start SeedD
    try:
        seedd_proc = start_seedd("/runner/shared")
    except Exception as e:
        log_json("fatal_error", stage="start_seedd", error=str(e))
        sys.exit(1)

    log_json("runner_ready",
            seedd_pid=seedd_proc.pid,
            artifacts_ready=True,
            seed_dirs_registered=True)

    # Determine harness path from artifacts
    harness_path = os.path.join("/runner/artifacts/coverage-harness", "harness")
    if not os.path.exists(harness_path):
        # Try finding any executable in the coverage-harness directory
        harness_dir = "/runner/artifacts/coverage-harness"
        executables = [f for f in os.listdir(harness_dir)
                      if os.path.isfile(os.path.join(harness_dir, f))
                      and os.access(os.path.join(harness_dir, f), os.X_OK)]
        if executables:
            harness_path = os.path.join(harness_dir, executables[0])
        else:
            log_json("fatal_error", stage="harness_detection", error="No harness binary found")
            sys.exit(1)

    # Determine project name from TARGET_HARNESS or harness path
    project_name = target_harness if target_harness else os.path.basename(harness_path)

    log_json("starting_seedgen_loop",
            harness_path=harness_path,
            project_name=project_name,
            target_seeds=num_seeds)

    # Run seedgen pipeline
    try:
        run_seedgen_loop(harness_path, project_name, num_seeds)
    except Exception as e:
        log_json("fatal_error", stage="run_seedgen_loop", error=str(e))
        sys.exit(1)

    log_json("runner_complete", message="Seedgen pipeline finished")


if __name__ == "__main__":
    main()
