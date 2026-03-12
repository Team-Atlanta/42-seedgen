# Testing Patterns

**Analysis Date:** 2026-03-11

## Test Framework

**Runner:**
- pytest - Configuration detected at `components/primefuzz/pytest.ini`
- No test files in the main `components/directed/` component
- Test suite exists in `components/primefuzz/tests/`

**Assertion Library:**
- Standard pytest assertions (no specialized assertion libraries detected)

**Run Commands:**
```bash
pytest                          # Run all tests (from project root with pytest.ini present)
pytest -v                       # Verbose test output
pytest tests/test_config.py     # Run specific test file
pytest -k test_crash_triager    # Run tests matching pattern
pytest --asyncio-mode=auto      # Run async tests (configured in pytest.ini)
```

**Configuration file:** `components/primefuzz/pytest.ini`
```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
log_cli = true
log_cli_level = INFO
```

## Test File Organization

**Location:**
- Tests are separate from source code - Located in `tests/` directory parallel to source modules
- Example structure: `components/primefuzz/tests/test_config.py`, `tests/test_triage_local.py`
- No tests detected in the main `components/directed/` component

**Naming:**
- Test files prefixed with `test_`: `test_config.py`, `test_triage_local.py`, `test_redis_middleware.py`
- Test functions prefixed with `test_`: `test_parse_database_url()`, `test_crash_triager_libpng()`, `test_config_from_env_with_database_url()`

**Structure:**
```
components/primefuzz/
├── modules/              # Source code
├── tests/                # Test directory
│   ├── test_config.py
│   ├── test_triage_local.py
│   ├── test_redis_middleware.py
│   ├── test_libfuzzer_log_parser.py
│   └── publish_test_message.py  # Utility for testing
└── pytest.ini
```

## Test Structure

**Suite Organization:**
```python
# From test_config.py - Fixture-based organization
@pytest.fixture
def mock_env_with_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL",
        "postgresql://jPbQIckk:Jt-N%2BP2erV%3D%7B2fvV@b3yond-postgres-dev.postgres.database.azure.com:5432/b3yond-db-dev")

@pytest.fixture
def mock_env_with_individual_vars(monkeypatch):
    monkeypatch.setenv("PG_CONNECTION_STRING", "postgresql://localhost:5432/testdb")
    monkeypatch.setenv("PG_USER", "test_user")
    monkeypatch.setenv("PG_PASSWORD", "test_pass")

def test_parse_database_url():
    url = "postgresql://jPbQIckk:Jt-N%2BP2erV%3D%7B2fvV@b3yond-postgres-dev.postgres.database.azure.com:5432/b3yond-db-dev"
    conn_string, user, password = Config.parse_database_url(url)

    assert "b3yond-postgres-dev.postgres.database.azure.com:5432/b3yond-db-dev" in conn_string
    assert user == "jPbQIckk"
    assert password == "Jt-N%2BP2erV%3D%7B2fvV"

def test_config_from_env_with_database_url(mock_env_with_database_url):
    config = Config.from_env()
    assert "b3yond-postgres-dev.postgres.database.azure.com" in config.pg_connection_string
```

**Patterns:**
- Fixtures handle setup: `mock_env_with_database_url`, `mock_env_with_individual_vars`
- Direct assertions for simple cases: `assert user == "jPbQIckk"`
- Fixture injection through function parameters: `def test_name(fixture_name):`
- No explicit teardown detected - pytest handles cleanup

## Mocking

**Framework:** pytest built-in `monkeypatch` fixture for environment variable mocking

**Patterns:**
```python
# From test_config.py - Environment variable mocking
@pytest.fixture
def mock_env_with_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://...")

def test_config_from_env_with_database_url(mock_env_with_database_url):
    config = Config.from_env()
    assert "b3yond-postgres-dev.postgres.database.azure.com" in config.pg_connection_string
```

**What to Mock:**
- Environment configuration (`DATABASE_URL`, connection strings, credentials)
- External service paths (not detected in current tests, but pattern shows fixture-based approach)

**What NOT to Mock:**
- Configuration parsing logic itself - tests exercise real parsing
- Core business logic - tests call actual methods with mocked inputs
- File system operations - use `tmp_path` fixture for temporary files

## Fixtures and Factories

**Test Data:**
```python
# From test_triage_local.py - Temporary file fixtures with binary data
@pytest.fixture
def testcase_path(tmp_path):
    test_case_file = tmp_path / "sample_data.bin"
    b64_data = "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgEAIAAACsiDHgAAAABHNCSVRnQU1BAAGGoDHoll9pQ0NQdFJOU///////..."
    test_file = Path(test_case_file)
    test_file.write_bytes(base64.b64decode(b64_data))
    return test_file

@pytest.fixture
def testcase_path_jvm(tmp_path):
    test_case_file = tmp_path / "sample_data.bin"
    b64_data = "Wlo6Ly8yNjg0Nzo2NDg5LzQ="
    test_file = Path(test_case_file)
    test_file.write_bytes(base64.b64decode(b64_data))
    return test_file
```

**Location:**
- Fixtures defined at top of test files using `@pytest.fixture` decorator
- Built-in fixtures used: `tmp_path` (temporary directory), `monkeypatch` (environment changes)

## Coverage

**Requirements:** Not enforced - No `.coveragerc` or coverage configuration detected

**View Coverage:**
- Coverage tool not configured
- Can be added manually: `pytest --cov=components/directed/src --cov-report=html`

## Test Types

**Unit Tests:**
- Focus on individual functions and configuration parsing
- Example: `test_parse_database_url()` tests URL parsing in isolation
- Example: `test_config_default_values()` tests Config default behavior
- Scope: Input validation, output correctness, error cases

**Integration Tests:**
- Tests involving async operations and external process execution
- Example: `test_crash_triager_libpng()` in `test_triage_local.py` - marked with `@pytest.mark.asyncio`
- Interacts with real fuzzing infrastructure: `triager.triage_crash("libpng", "libpng_read_fuzzer", testcase_path)`
- Validates return types and values: `assert isinstance(crash_info, CrashInfo)`, `assert "AddressSanitizer" in crash_info.bug_type`

**E2E Tests:**
- Not detected in current test suite
- Manual testing approach appears primary for end-to-end scenarios

## Common Patterns

**Async Testing:**
```python
# From test_triage_local.py - Async test with pytest-asyncio
@pytest.mark.asyncio
async def test_crash_triager_libpng(testcase_path):
    triager = CrashTriager(Path(OSS_FUZZ_PATH))
    crash_info = await triager.triage_crash(
        "libpng", "libpng_read_fuzzer", testcase_path
    )

    assert isinstance(crash_info, CrashInfo)
    assert "AddressSanitizer" in crash_info.bug_type
```

**Error Testing:**
```python
# Pattern: Test expected values to verify correct behavior
# From test_triage_local.py
assert crash_info.dup_token == "OSS_FUZZ_png_handle_iCCP--OSS_FUZZ_png_read_info--LLVMFuzzerTestOneInput"

# Pattern: Test for presence of expected strings
assert "dynamic-stack-buffer-overflow" in crash_info.bug_type
assert "FuzzerSecurityIssue" in crash_info.bug_type
```

**Data-Driven Tests:**
```python
# Pattern: Multiple test cases with different inputs through fixtures
def test_config_from_env_with_database_url(mock_env_with_database_url):
    ...

def test_config_from_env_with_individual_vars(mock_env_with_individual_vars):
    ...

def test_config_default_values():
    ...
```

## Test Organization Summary

**Main testing locations:**
- `components/primefuzz/tests/` - Configuration and crash triage tests
- `components/slice/oss-fuzz-aixcc/infra/` - Infrastructure tests (separate suite)

**Main directed component:**
- `components/directed/src/` - No local tests detected
- Testing likely performed through integration tests or manual testing with mock server (`src/mock/mockserver.py`)

**Mock infrastructure available in source:**
- `src/mock/mockconfig.py` - Mock configuration builder
- `src/mock/mockserver.py` - Mock server for development/testing
- Enables running application without external services via `--mock` flag

---

*Testing analysis: 2026-03-11*
