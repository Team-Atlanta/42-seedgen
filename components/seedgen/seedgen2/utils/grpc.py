# utils/grpc.py
# This file contains a helper wrapper for gRPC calls to SeedD.

import functools
import time
import grpc
import os
import shutil
import uuid
import logging
import grpc_health.v1.health_pb2 as health_pb2
import grpc_health.v1.health_pb2_grpc as health_pb2_grpc
from typing import List, Optional, cast

from seedgen2.protobuf import seedd_pb2
from seedgen2.protobuf import seedd_pb2_grpc
import grpc.aio

DEFAULT_PORT = 9002
DEFAULT_TIMEOUT = 30  # seconds
DEFAULT_RETRY_INTERVAL = 3  # second

logger = logging.getLogger(__name__)


def grpc_call(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.time()
        last_error = None
        attempt = 0

        logger.info(f"[grpc_call] Starting call to {func.__name__} on {self.ip_addr}:{DEFAULT_PORT}")

        while time.time() - start_time < DEFAULT_TIMEOUT:
            attempt += 1
            try:
                logger.info(f"[grpc_call] Attempt {attempt}: health check...")
                self.health_check()
                logger.info(f"[grpc_call] Health check passed, calling {func.__name__}")
                return func(self, *args, **kwargs)
            except grpc.RpcError as rpc_error:
                last_error = rpc_error
                # Cast the error to grpc.Call to satisfy type checker
                error = rpc_error if isinstance(
                    rpc_error, grpc.Call) else rpc_error
                if isinstance(error, grpc.Call):
                    code = error.code()
                    details = error.details()
                    logger.warning(f"[grpc_call] Attempt {attempt}: gRPC error - code={code.name}, details={details}")

                    if code == grpc.StatusCode.UNAVAILABLE:
                        logger.info(f"[grpc_call] Server unavailable, sleeping {DEFAULT_RETRY_INTERVAL}s before retry...")
                        time.sleep(DEFAULT_RETRY_INTERVAL)
                        self.recreate_channel()
                        continue
                    elif code == grpc.StatusCode.INVALID_ARGUMENT:
                        raise ValueError(
                            "Invalid arguments provided to gRPC call") from rpc_error
                    elif code == grpc.StatusCode.NOT_FOUND:
                        raise FileNotFoundError(
                            "Requested resource not found") from rpc_error
                    else:
                        raise RuntimeError(
                            f"gRPC call failed: {details} (Code: {code.name})"
                        ) from rpc_error
                else:
                    logger.warning(f"[grpc_call] Attempt {attempt}: RpcError (not grpc.Call): {rpc_error}")
            except Exception as e:
                logger.error(f"[grpc_call] Attempt {attempt}: Non-gRPC exception: {type(e).__name__}: {e}")
                raise

        # If we've exhausted our retries, raise the last error
        logger.error(f"[grpc_call] Exhausted {attempt} attempts over {DEFAULT_TIMEOUT}s, last_error={last_error}")
        raise RuntimeError(
            f"gRPC server remained unavailable after {DEFAULT_TIMEOUT} seconds"
        ) from last_error
    return wrapper


class SeedD:
    def __init__(self, ip_addr: str, shared_dir: str):
        self.ip_addr = ip_addr
        # the directory is shared across the container and host machine
        self.shared_dir = shared_dir
        logger.info(f"[SeedD] Initializing connection to {ip_addr}:{DEFAULT_PORT}")
        self.channel = grpc.insecure_channel(f"{ip_addr}:{DEFAULT_PORT}")
        self.stub = seedd_pb2_grpc.SeedDStub(self.channel)
        self.health_stub = health_pb2_grpc.HealthStub(self.channel)
        logger.info(f"[SeedD] Channel created, shared_dir={shared_dir}")

    def recreate_channel(self):
        logger.info(f"[SeedD] Recreating channel to {self.ip_addr}:{DEFAULT_PORT}")
        self.channel.close()
        self.channel = grpc.insecure_channel(f"{self.ip_addr}:{DEFAULT_PORT}")
        self.stub = seedd_pb2_grpc.SeedDStub(self.channel)
        self.health_stub = health_pb2_grpc.HealthStub(self.channel)

    def health_check(self):
        """Performs a health check on the gRPC server."""
        response = self.health_stub.Check(health_pb2.HealthCheckRequest(), timeout=5)
        logger.debug(f"[SeedD] Health check response: status={response.status}")

    def share_file(self, file_path: str):
        # Generate a UUID for the file to avoid name conflicts
        base_name, ext = os.path.splitext(os.path.basename(file_path))
        unique_filename = f"{uuid.uuid4()}_{base_name}{ext}"
        container_path = os.path.join("/shared", unique_filename)
        shutil.copy(file_path, os.path.join(self.shared_dir, unique_filename))
        return container_path

    @grpc_call
    def run_seeds(self, harness_binary: str, seeds_path: List[str]) -> seedd_pb2.RunSeedsResponse:
        """Runs the seeds and returns the coverage."""
        request = seedd_pb2.RunSeedsRequest(
            harness_binary=harness_binary, seeds_path=seeds_path)
        return self.stub.RunSeeds(request, compression=grpc.Compression.Gzip)

    @grpc_call
    def get_merged_coverage(self, harness_binary: str) -> seedd_pb2.RunSeedsResponse:
        """Gets the merged coverage for a harness."""
        request = seedd_pb2.GetMergedCoverageRequest(
            harness_binary=harness_binary)
        return self.stub.GetMergedCoverage(request, compression=grpc.Compression.Gzip)

    @grpc_call
    def get_region_source(
        self,
        filepath: str,
        start_line: int,
        start_column: int,
        end_line: int,
        end_column: int
    ) -> seedd_pb2.GetRegionSourceResponse:
        """Gets the source code for a region."""
        request = seedd_pb2.GetRegionSourceRequest(
            filepath=filepath,
            start_line=start_line,
            start_column=start_column,
            end_line=end_line,
            end_column=end_column
        )
        return self.stub.GetRegionSource(request, compression=grpc.Compression.Gzip)

    @grpc_call
    def extract_function_source(
        self,
        filepath: str,
        line: Optional[int] = None,
        function_name: Optional[str] = None
    ) -> seedd_pb2.ExtractFunctionSourceResponse:
        """Extracts the source code for a function."""
        if not (line or function_name):
            raise ValueError(
                "Must provide either line number or function name")
        if line and function_name:
            raise ValueError(
                "Cannot provide both line number and function name")
        request = seedd_pb2.ExtractFunctionSourceRequest(filepath=filepath)
        if line:
            request.line = line
        elif function_name:
            request.function_name = function_name
        return self.stub.ExtractFunctionSource(request, compression=grpc.Compression.Gzip)

    @grpc_call
    def get_call_graph(self, harness_binary: str) -> seedd_pb2.GetCallGraphResponse:
        """Gets the call graph for a harness."""
        request = seedd_pb2.GetCallGraphRequest(harness_binary=harness_binary)
        return self.stub.GetCallGraph(request, compression=grpc.Compression.Gzip)

    @grpc_call
    def get_functions(self, harness_binary: str) -> seedd_pb2.GetFunctionsResponse:
        """Gets the functions for a harness."""
        request = seedd_pb2.GetFunctionsRequest(harness_binary=harness_binary)
        return self.stub.GetFunctions(request, compression=grpc.Compression.Gzip)
