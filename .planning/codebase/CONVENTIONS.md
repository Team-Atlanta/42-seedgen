# Coding Conventions

**Analysis Date:** 2026-03-11

## Naming Patterns

**Files:**
- Snake case for all Python files: `daemon.py`, `fuzzer_runner.py`, `directed_msg.py`
- Descriptive names indicating purpose/responsibility: `crash_handler.py`, `seed_syncer.py`, `workspace.py`
- Modules grouped by function: `modules/` directory contains `patch_runner.py`, `telemetry.py`, `diff_parser.py`

**Functions:**
- Snake case consistently used: `safe_extract_tar()`, `generate_random_sha256()`, `get_file_sha256()`
- Private methods prefixed with single underscore: `_task_thread()`, `_on_message()`, `_get_task_metadata()`
- Action-oriented names: `handle_crash()`, `apply_patch()`, `prepare_workspace()`, `run_fuzzer_with_pid()`
- Context-specific naming: `_send_slice_request_and_wait()`, `_parse_and_validate_message()`, `_prepare_and_run_fuzzer()`

**Variables:**
- Snake case for all local and instance variables: `task_id`, `project_name`, `harness_name`, `result_path`
- Abbreviated names for message objects: `dmsg` (DirectedMsg), `slice_msg` (SliceMsg)
- Descriptive compound names: `current_time`, `focused_repo`, `storage_dir`, `workspace_dir`
- Enum-like collections as plural nouns: `harnesses`, `containers`, `observers`, `syncers`

**Types:**
- Dataclass names using PascalCase: `DirectedMsg`, `SliceMsg`, `CrashInfo`
- Class names using PascalCase: `DirectedDaemon`, `FuzzerRunner`, `WorkspaceManager`, `CrashHandler`
- Enum classes suffixed with `Enum`: `TaskTypeEnum`, `TaskStatusEnum`, `SanitizerEnum`, `FuzzerTypeEnum`
- Exception classes suffixed with `Exception`: `SkipTaskException`

## Code Style

**Formatting:**
- Standard Python conventions observed (no linter config detected)
- Line length varies but generally readable (max ~100 characters observed)
- Import statements organized into groups

**Linting:**
- Not detected - No `.pylintrc`, `.flake8`, or `setup.cfg` config files present in the directed component
- Custom code patterns enforced through exception handling and type annotations

## Import Organization

**Order:**
1. Standard library imports (pathlib, threading, logging, time, etc.)
2. Third-party imports (docker, pika, sqlalchemy, redis, opentelemetry, watchdog)
3. Local application imports (config, daemon, db, utils modules)

**Path Aliases:**
- No explicit path aliases used - imports use relative paths from src root
- Module imports follow directory structure: `from daemon.modules.patch_runner import PatchManager`
- Database imports centralized: `from db.db import DBConnection`, `from db.models.fuzz_related import Bug, Seed`

**Examples from `daemon.py`:**
```python
from pathlib import Path
import threading
import time
import logging
from typing import List
import uuid
import json
import shutil
import os
import tarfile
import docker
import redis
import re
from redis.sentinel import Sentinel
from dataclasses import asdict
from config.config import Config
import pika
from sqlalchemy import select
from daemon.modules.patch_runner import PatchManager
from daemon.modules.fuzzer_runner import FuzzerRunner
from daemon.modules.workspace import WorkspaceManager
from db.models.directed_slice import DirectedSlice
from utils.msg import MsgQueue, SkipTaskException
```

## Error Handling

**Patterns:**
- Try-except blocks for external operations (message queue, database, file system)
- Custom exception classes for semantic clarity: `SkipTaskException(task_id, reason)` for intentional skips
- Exception re-raising pattern: Catch, log details with context, then raise or handle gracefully
- Defensive checks before operations: `if not workspace:`, `if not focused_repo:`, `if not result_path:`

**Examples:**
```python
# From daemon.py - Graceful exception handling with semantic context
try:
    dmsg = DirectedMsg(**json.loads(body))
except Exception as e:
    logging.error('Failed to parse message: %s', e)
    raise SkipTaskException(None, 'Invalid message format')

# From msg.py - Custom exception for task skipping
except SkipTaskException as e:
    logging.info(f"Skipping task: {e.reason}")
    cb = functools.partial(self._ack_message, ch, method.delivery_tag)
    connection.add_callback_threadsafe(cb)
    return
except Exception as e:
    logging.error('Failed to process message: %s', e)
    cb = functools.partial(self._ack_message, ch, method.delivery_tag, nack=True)
    connection.add_callback_threadsafe(cb)

# From misc.py - Validation errors with descriptive messages
if not str(member_path).startswith(str(extract_path)):
    raise RuntimeError(f"Unsafe extraction detected: {member_path}")

# From fuzzer_runner.py - Resource validation
if not focused_repo:
    raise ValueError("Focused repository not found in the workspace.")
```

## Logging

**Framework:** Python's standard `logging` module

**Configuration:** Custom formatter in `utils/logs.py`
- Level-specific ANSI color codes for console output
- Format: `[SYMBOL] asctime | module | message (filename:lineno)`
- Symbols: `[*]` (DEBUG), `[+]` (INFO), `[!]` (WARNING/CRITICAL), `[X]` (ERROR)

**Patterns:**
- Always include context identifiers when available: `Task %s |`, `Project %s`, task_id
- Use appropriate levels: INFO for state changes, DEBUG for detailed flow, WARNING for potential issues, ERROR for failures
- Paired logging: Most operations log at start (INFO) and end (DEBUG) or errors (ERROR)

**Examples from `daemon.py`:**
```python
logging.info('Task %s | Delta fuzzing', dmsg.task_id)
logging.debug('Task %s | Modified functions: %s', dmsg.task_id, modified_functions)
logging.warning('Task %s | No changed functions detected in the patch', dmsg.task_id)
logging.error('Task %s | Slicing R14 failed, trying R18', dmsg.task_id)
logging.debug("Slice target | %s", entry)
```

**Initialization:** `init_logging(debug=False)` from `utils.logs` sets root logger level and applies custom formatter

## Comments

**When to Comment:**
- Not heavily commented - relies on descriptive names and structure
- Comments used for non-obvious logic (e.g., line 10 in `crash_handler.py`: `# ! Why we need PollingObserver: <url>`)
- Commented-out code preserved in some places with reasoning (e.g., daemon.py lines 112, 253)
- Configuration explanations (e.g., line 8 in `db.py`: `# Disable expiration so that objects remain accessible after commit.`)

**JSDoc/TSDoc:**
- Uses Python docstrings with triple quotes
- Short descriptions followed by Args/Returns sections
- Example from `fuzzer_runner.py`:
```python
"""
Initializes FuzzerRunner with data from DirectedMsg and the WorkspaceManager.

Args:
    directed_msg (DirectedMsg): Contains task and project details.
    workspace_manager (WorkspaceManager): Manages the task workspace.
    base_runner_image (str): Base runner image for fuzzing containers.
    image_prefix (str): Prefix for the project-specific Docker image.
"""
```

## Function Design

**Size:** Methods typically 10-50 lines; longer methods (100+ lines) decomposed into helpers
- Example: `daemon.py._on_message()` at 56 lines delegates to smaller methods like `_handle_delta_fuzzing()`, `_handle_slicing()`
- Properties used to encapsulate computed values: `output_dir` property in `FuzzerRunner` (lines 67-73)

**Parameters:**
- Type hints used extensively: `def __init__(self, msg_queue: MsgQueue, debug = False, mock = False, redis_url = None)`
- Union types with modern syntax: `-> Path | None` (daemon.py line 78)
- Optional parameters with defaults: `def seedgen_dir(self, harness_name: str) -> Path`
- Context managers used for resource management: `__enter__()` and `__exit__()` in `WorkspaceManager`

**Return Values:**
- Explicit None returns for conditional paths: Returns `None` when validation fails
- Tuple unpacking for multiple returns: `conn_string, user, password = Config.parse_database_url(url)`
- Descriptive return types with unions: `-> Path | None` indicates success path

## Module Design

**Exports:**
- Classes designed as single responsibility units with clear public interfaces
- Private methods indicate internal implementation details
- Dataclasses (`DirectedMsg`, `SliceMsg`) used as message carriers

**Barrel Files:**
- Not used - imports are explicit from specific modules
- Example: `from daemon.modules.patch_runner import PatchManager` rather than from `daemon.modules`

**Decorators:**
- Custom decorator `@span_decorator()` used for telemetry/tracing (daemon/modules/telemetry.py)
- Example usage: `@span_decorator("Sends a slice request...")` wraps methods with span creation and error handling

---

*Convention analysis: 2026-03-11*
