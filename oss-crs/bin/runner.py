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
        ("harness", "/runner/artifacts/harness"),
        ("compile-commands", "/runner/artifacts/compile-commands"),
        ("source-tree", "/src"),
    ]

    for artifact_name, artifact_path in artifacts:
        log_json("downloading_artifact", name=artifact_name, path=artifact_path)
        result = subprocess.run(
            ["libCRS", "download-build-output", artifact_name, artifact_path],
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



def setup_seedd_artifacts():
    """
    Set up /out directory with artifacts for SeedD.
    SeedD expects harness binaries and compile_commands in /out.
    """
    log_json("setup_seedd_artifacts_start")

    # Ensure /out exists
    os.makedirs("/out", exist_ok=True)

    # Symlink harness binaries to /out (single binary has both coverage + callgraph)
    harness_dir = "/runner/artifacts/harness"
    for item in os.listdir(harness_dir):
        src = os.path.join(harness_dir, item)
        dst = os.path.join("/out", item)
        if os.path.isfile(src) and not os.path.exists(dst):
            os.symlink(src, dst)
            log_json("artifact_linked", src=src, dst=dst)

    # Symlink compile_commands directory
    compile_cmd_src = "/runner/artifacts/compile-commands"
    compile_cmd_dst = "/out/compile_commands"
    if os.path.exists(compile_cmd_src) and not os.path.exists(compile_cmd_dst):
        os.symlink(compile_cmd_src, compile_cmd_dst)
        log_json("artifact_linked", src=compile_cmd_src, dst=compile_cmd_dst)

    # Symlink LLVM tools to /usr/local/bin so getcov can find them
    for tool in ["llvm-profdata", "llvm-cov"]:
        src = f"/runner/artifacts/harness/{tool}"
        dst = f"/usr/local/bin/{tool}"
        if os.path.exists(src):
            # Remove existing symlink/file if present
            if os.path.exists(dst) or os.path.islink(dst):
                os.remove(dst)
            os.symlink(src, dst)
            log_json("llvm_tool_linked", tool=tool, src=src, dst=dst)

    log_json("setup_seedd_artifacts_complete")


def register_seed_dirs():
    """Register seed output directory with libCRS (spawns background daemon)."""
    log_json("register_seed_dirs_start")

    # Note: libCRS register-* commands fork a background daemon process.
    # Don't use capture_output=True as it blocks on the daemon's inherited pipes.
    # The parent process prints "Started daemon with PID: X" and exits immediately.

    # Register submit directory for generated seeds
    # This spawns a daemon that auto-syncs new files to OSS_CRS_SUBMIT_DIR
    result = subprocess.run(
        ["libCRS", "register-submit-dir", "seed", "/runner/seeds-out"],
        text=True
    )
    if result.returncode != 0:
        log_json("register_submit_failed", returncode=result.returncode)
        raise RuntimeError(f"Failed to register submit directory (exit code {result.returncode})")
    log_json("submit_dir_registered", path="/runner/seeds-out", type="seed")

    log_json("register_seed_dirs_complete")


def start_seedd() -> subprocess.Popen:
    """
    Start SeedD gRPC server as background process and wait for gRPC health check.

    Returns:
        Popen object for running SeedD process

    Raises:
        RuntimeError: If SeedD fails to start or health check timeout
    """
    import grpc
    import grpc_health.v1.health_pb2 as health_pb2
    import grpc_health.v1.health_pb2_grpc as health_pb2_grpc

    log_json("start_seedd")

    # Start SeedD as subprocess — stderr goes to our stderr for visibility in logs
    proc = subprocess.Popen(
        ["/usr/local/bin/seedd"],
        stdout=subprocess.PIPE,
        stderr=sys.stderr
    )

    log_json("seedd_process_started", pid=proc.pid)

    # Health check loop - wait for gRPC server to be ready
    max_attempts = 60
    sleep_interval = 1

    for attempt in range(1, max_attempts + 1):
        # Check if process died
        if proc.poll() is not None:
            stdout, stderr = proc.communicate()
            log_json("seedd_died",
                    returncode=proc.returncode,
                    stdout=stdout.decode() if stdout else "",
                    stderr=stderr.decode() if stderr else "")
            raise RuntimeError(f"SeedD process died with return code {proc.returncode}")

        # Try actual gRPC health check
        try:
            channel = grpc.insecure_channel("localhost:9002")
            health_stub = health_pb2_grpc.HealthStub(channel)
            health_stub.Check(health_pb2.HealthCheckRequest(), timeout=2)
            channel.close()
            log_json("seedd_health_check_passed", attempt=attempt)
            log_json("seedd_ready", pid=proc.pid)
            return proc
        except grpc.RpcError as e:
            log_json("seedd_health_check_retry", attempt=attempt, error=str(e))
        except Exception as e:
            log_json("seedd_health_check_retry", attempt=attempt, error=str(e))

        time.sleep(sleep_interval)

    # Health check timeout - get SeedD output for debugging
    proc.terminate()
    try:
        stdout, stderr = proc.communicate(timeout=5)
        log_json("seedd_health_timeout", max_attempts=max_attempts,
                stdout=stdout.decode() if stdout else "",
                stderr=stderr.decode() if stderr else "")
    except:
        log_json("seedd_health_timeout", max_attempts=max_attempts)
    raise RuntimeError(f"SeedD gRPC health check timeout after {max_attempts} attempts")


def run_seedgen_loop(harness_path: str, project_name: str, num_seeds: int, seedd_proc: subprocess.Popen):
    """
    Run seedgen pipeline in a loop.

    Args:
        harness_path: Path to coverage harness binary
        project_name: Name of target project
        num_seeds: Target number of seeds to generate
        seedd_proc: Running SeedD process
    """
    result_dir = "/runner/seeds-out"
    os.makedirs(result_dir, exist_ok=True)

    iteration = 0
    while True:
        iteration += 1

        # Check if seedd is still running before each iteration
        if seedd_proc.poll() is not None:
            # Seedd died - get its output
            stdout, stderr = seedd_proc.communicate()
            log_json("seedd_died_during_loop",
                    iteration=iteration,
                    returncode=seedd_proc.returncode,
                    stdout=stdout.decode() if stdout else "",
                    stderr=stderr.decode() if stderr else "")
            raise RuntimeError(f"SeedD died with return code {seedd_proc.returncode}")

        log_json("pipeline_start", iteration=iteration, seedd_pid=seedd_proc.pid)

        # Get model name from env (set by compose.yaml) or use default
        gen_model = os.getenv("SEEDGEN_GENERATIVE_MODEL", "claude-3.5-sonnet")

        # Pass just the basename since seedd joins it with /out
        harness_basename = os.path.basename(harness_path)
        agent = SeedGenAgent(
            result_dir=result_dir,
            ip_addr="localhost",
            project_name=project_name,
            harness_binary=harness_basename,
            gen_model=gen_model
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
            # Check if seedd died
            if seedd_proc.poll() is not None:
                stdout, stderr = seedd_proc.communicate()
                log_json("seedd_died_on_error",
                        iteration=iteration,
                        returncode=seedd_proc.returncode,
                        stdout=stdout.decode() if stdout else "",
                        stderr=stderr.decode() if stderr else "")
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

    # Setup /out directory for SeedD
    try:
        setup_seedd_artifacts()
    except Exception as e:
        log_json("fatal_error", stage="setup_seedd_artifacts", error=str(e))
        sys.exit(1)

    # Register seed directories
    try:
        register_seed_dirs()
    except Exception as e:
        log_json("fatal_error", stage="register_seed_dirs", error=str(e))
        sys.exit(1)

    # Create /shared for SeedD <-> seedgen file exchange
    os.makedirs("/shared", exist_ok=True)

    # Start SeedD
    try:
        seedd_proc = start_seedd()
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
        run_seedgen_loop(harness_path, project_name, num_seeds, seedd_proc)
    except Exception as e:
        log_json("fatal_error", stage="run_seedgen_loop", error=str(e))
        sys.exit(1)

    log_json("runner_complete", message="Seedgen pipeline finished")


if __name__ == "__main__":
    main()
