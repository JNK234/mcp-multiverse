# Testing Patterns

**Analysis Date:** 2026-01-26

## Test Framework

**Runner:**
- pytest 8.0+ (from `pyproject.toml` line 26)
- Configuration: `pyproject.toml` lines 53-55
- Config file: `tests/conftest.py` (minimal, mostly empty)

**Assertion Library:**
- pytest's built-in assertions: `assert condition`, `assert x == y`
- pytest.raises() for exception testing

**Run Commands:**
```bash
pytest tests                          # Run all tests with coverage
pytest tests -v                       # Verbose mode
pytest tests -v --cov=mcpx --cov-report=term-missing  # With coverage report
pytest tests/test_config.py           # Run specific test file
pytest tests/test_config.py::test_get_config_path  # Run specific test
pytest tests -k "test_valid"          # Run tests matching pattern
```

## Test File Organization

**Location:**
- Co-located with source: `tests/` directory mirrors `src/mcpx/` structure
- Pattern: `tests/test_<module>.py` for `src/mcpx/<module>.py`
- Platform tests in subdirectory: `tests/test_platforms/`

**Naming:**
- Test files: `test_*.py`
- Test classes: `Test<Functionality>` (PascalCase)
- Test methods: `test_<scenario>` (lowercase with underscores)
- Examples:
  - `test_config.py::TestLoadConfig` (class with multiple test methods)
  - `test_validation.py::TestValidateServer` (focused test class)
  - `test_health_check.py::TestIntegrationSubprocessSpawn` (integration tests)

**Structure:**
```
tests/
├── __init__.py              # Package marker
├── conftest.py              # pytest configuration and fixtures
├── fixtures/                # Test data fixtures
├── test_platforms/          # Platform-specific tests
│   ├── test_claude.py
│   ├── test_gemini.py
│   └── ...
├── test_config.py
├── test_validation.py
├── test_health_check.py
└── test_cli_add_remove.py
```

## Test Structure

**Suite Organization:**
```python
# tests/test_validation.py (example pattern)
class TestValidateCommandExists:
    """Tests for validate_command_exists function."""

    def test_valid_command_returns_none(self):
        """Test that existing command returns None."""
        result = validate_command_exists("python")
        assert result is None

    def test_invalid_command_returns_error(self):
        """Test that non-existent command returns ValidationError."""
        result = validate_command_exists("definitely_not_a_real_command_xyz123")
        assert result is not None
        assert result.severity == "error"
        assert "not found" in result.message.lower()

class TestValidateServer:
    """Tests for validate_server function."""
    # More tests here
```

**Patterns:**

1. **Arrange-Act-Assert (AAA):**
```python
def test_load_valid_config(tmp_path):
    """Test loading a valid JSON config file."""
    # ARRANGE: Create test data
    config_file = tmp_path / "config.json"
    config_content = {
        "mcpx": {"version": "1.0"},
        "servers": {"filesystem": {"type": "stdio", "command": "npx", "args": [...]}}
    }
    config_file.write_text(json.dumps(config_content, indent=2))

    # ACT: Call the function
    config = load_config(config_file)

    # ASSERT: Verify results
    assert config.version == "1.0"
    assert len(config.servers) == 1
```

2. **Exception Testing:**
```python
def test_load_config_missing_file(tmp_path):
    """Test loading non-existent config file."""
    config_file = tmp_path / "nonexistent.json"

    with pytest.raises(FileNotFoundError, match="Config file not found"):
        load_config(config_file)
```

3. **Parameterized Tests:**
Not heavily used; when needed, test methods with descriptive names instead of parametrize

## Mocking

**Framework:** unittest.mock (standard library)

**Patterns:**
```python
# tests/test_health_check.py (example)
from unittest.mock import MagicMock, patch

def test_health_check_with_timeout():
    """Test health check timeout handling."""
    with patch('subprocess.Popen') as mock_popen:
        mock_popen.side_effect = subprocess.TimeoutExpired("cmd", 5)

        server = MCPServer(name="test", type="stdio", command="echo")
        success, message = health_check_stdio_server(server, timeout=5)

        assert success is False
        assert "timed out" in message.lower()
```

**What to Mock:**
- External subprocess calls (subprocess.Popen)
- Network calls (urllib.request.urlopen)
- System calls (os.environ, shutil.which)
- File I/O when testing logic separate from file operations

**What NOT to Mock:**
- Real command execution for integration tests (test with real `echo`, `python`, `cat` commands)
- JSON parsing/serialization (test with real json module)
- Data structures (actual MCPServer, Config objects)
- Local file operations in integration tests

**Fixtures:**
```python
# tests/conftest.py
# Minimal configuration - pytest built-in fixtures used:
# - tmp_path: temporary directory for each test
# - monkeypatch: for modifying environment variables
```

## Fixtures and Factories

**Test Data:**
- Inline creation in test methods (no factory classes)
- Direct dictionary/dataclass construction
- Example from `tests/test_config.py` (lines 26-46):
```python
config_content = {
    "mcpx": {"version": "1.0"},
    "servers": {
        "filesystem": {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/projects"]
        },
        "github": {
            "type": "stdio",
            "command": "npx",
            "env": {"TOKEN": "test"}
        }
    }
}
config_file.write_text(json.dumps(config_content, indent=2))
config = load_config(config_file)
```

**Fixtures Location:**
- `tests/fixtures/` directory exists but minimally used
- Most tests create their own test data inline
- pytest's tmp_path fixture used heavily: `def test_func(tmp_path):`
- monkeypatch fixture for environment variables: `def test_func(monkeypatch):`

## Coverage

**Requirements:**
- Target: not explicitly enforced, but tests aim for comprehensive coverage
- Coverage report generated in pytest.ini options (line 55): `--cov=mcpx --cov-report=term-missing`

**View Coverage:**
```bash
pytest tests --cov=mcpx --cov-report=term-missing   # Show missing line numbers
pytest tests --cov=mcpx --cov-report=html           # Generate HTML report
cat .coverage                                        # Coverage data file exists
```

## Test Types

**Unit Tests:**
- Scope: Individual functions in isolation
- Approach: Test single function with mocked dependencies
- Examples:
  - `test_validate_command_exists()` (no side effects, pure logic)
  - `test_get_config_path()` (simple accessor)
  - Validation tests with mocked environment variables

**Integration Tests:**
- Scope: Real subprocess/network calls
- Approach: Test with actual system resources (subprocess.Popen, urllib)
- Test class prefix: `TestIntegration*` (explicit marking)
- Examples in `tests/test_health_check.py`:
  - `TestIntegrationValidateCommandExists` (lines 28-55): Real system commands (echo, python, cat)
  - `TestIntegrationSubprocessSpawn` (lines 57-101): Real subprocess creation and stdio communication
- Rationale: Health checks need real subprocess behavior to validate correctness

**E2E Tests:**
- Not present in this codebase
- Integration tests cover end-to-end CLI flows (test_cli_integration.py exists)

## Common Patterns

**Async Testing:**
Not applicable - codebase uses synchronous I/O and subprocess calls

**Error Testing:**
```python
# Pattern from tests/test_validation.py (lines 48-59)
def test_missing_command_fails(self):
    """Test that server with missing command fails validation."""
    server = MCPServer(
        name="broken-server",
        type="stdio",
        command="nonexistent_command_xyz"
    )
    errors = validate_server(server)
    assert len(errors) == 1
    assert errors[0].severity == "error"
    assert errors[0].server_name == "broken-server"
    assert "not found" in errors[0].message.lower()
```

**Environment Variable Testing:**
```python
# Pattern from tests/test_config.py (lines 204-230)
def test_load_config_with_env_expansion(tmp_path, monkeypatch):
    """Test that environment variables are expanded during loading."""
    # Use monkeypatch fixture to set environment variables
    monkeypatch.setenv("HOME", "/home/testuser")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

    # Create config with env var references
    config_content = {
        "servers": {
            "filesystem": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "server", "${HOME}/projects"],
                "env": {"TOKEN": "${GITHUB_TOKEN}"}
            }
        }
    }
    config_file.write_text(json.dumps(config_content, indent=2))

    # Load and verify expansion happened
    config = load_config(config_file)
    fs_server = config.servers["filesystem"]
    assert fs_server.args == ["-y", "server", "/home/testuser/projects"]
    assert fs_server.env == {"TOKEN": "ghp_test_token"}
```

**Edge Case Testing:**
```python
# Pattern from tests/test_health_check.py (lines 75-88)
def test_integration_real_subprocess_cat_with_stdin(self):
    """Test that cat command receives stdin correctly."""
    server = MCPServer(name="cat-test", type="stdio", command="cat", args=[])
    success, message = health_check_stdio_server(server, timeout=2)
    # cat will echo back stdin - verify process runs without hanging
    assert success is False or success is True  # Both states valid
    assert "cat-test" in message
```

**Subprocess/Timeout Testing:**
```python
# From tests/test_health_check.py - subprocess tests with mock and real
class TestMockSubprocessTimeout:
    """Unit tests with mocked subprocess."""

    def test_health_check_timeout_handling(self):
        """Test timeout handling in health check."""
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.side_effect = subprocess.TimeoutExpired("cmd", 5)

            server = MCPServer(name="test", type="stdio", command="echo")
            success, message = health_check_stdio_server(server, timeout=5)

            assert success is False
            assert "timed out" in message.lower()

class TestIntegrationSubprocessSpawn:
    """Integration tests with real subprocess."""

    def test_integration_real_subprocess_echo(self):
        """Test that a real echo process can be spawned."""
        server = MCPServer(
            name="echo-test",
            type="stdio",
            command="echo",
            args=['{"jsonrpc":"2.0","id":1,"result":{"serverInfo":{"name":"test","version":"1.0"}}}']
        )
        success, message = health_check_stdio_server(server, timeout=5)
        assert isinstance(success, bool)
        assert "echo-test" in message
```

---

*Testing analysis: 2026-01-26*
