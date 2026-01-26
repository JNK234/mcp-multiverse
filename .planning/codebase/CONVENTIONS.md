# Coding Conventions

**Analysis Date:** 2026-01-26

## Naming Patterns

**Files:**
- Module files use lowercase with underscores: `config.py`, `validation.py`, `toml_writer.py`
- Test files use `test_` prefix: `test_config.py`, `test_validation.py`, `test_cli_add_remove.py`
- No abbreviations in file names

**Functions:**
- Use snake_case: `validate_command_exists()`, `health_check_stdio_server()`, `get_config_path()`
- Command handler functions use `cmd_` prefix: `cmd_sync()`, `cmd_add()`, `cmd_remove()`, `cmd_list()`, `cmd_validate()`
- Helper functions clearly describe their purpose with full words

**Variables:**
- Use snake_case throughout: `server_name`, `config_path`, `server_type`, `env_vars`, `http_servers`
- Single letter variables only in loops: `for cmd in commands:`, `for key, value in server.env.items():`
- Avoid abbreviations: write `server_count` not `srv_cnt`

**Types:**
- Use PascalCase for classes: `MCPServer`, `Config`, `ValidationError`, `SyncReport`, `PlatformAdapter`
- Constants in UPPER_CASE: `EXIT_SUCCESS`, `HEALTH_CHECK_TIMEOUT`, `CONFIG_DIR`, `CONFIG_FILE`, `MCP_PROTOCOL_VERSION`
- Type aliases (in lowercase): `ServerData = dict[str, str | list[str] | dict[str, str]]`

## Code Style

**Formatting:**
- Tool: ruff (formatter)
- Line length: 100 characters (set in `pyproject.toml` line 44)
- Indentation: 4 spaces

**Linting:**
- Tool: ruff (linter) with strict rule set
- Rules selected: `E, F, I, N, W, UP, B, C4, SIM` (from `pyproject.toml` line 47)
  - `E`: PEP8 errors
  - `F`: PyFlakes
  - `I`: isort import sorting
  - `N`: pep8-naming
  - `W`: Warnings
  - `UP`: pyupgrade
  - `B`: flake8-bugbear
  - `C4`: flake8-comprehensions
  - `SIM`: flake8-simplify

**Type Checking:**
- Tool: mypy with strict mode enabled
- Python version target: 3.12+ (from `pyproject.toml` line 50)
- All files use proper type hints

## Import Organization

**Order:**
1. Standard library imports: `import argparse`, `import json`, `import os`, `from pathlib import Path`
2. Third-party imports: `import tomli`, `import pytest`
3. Local imports: `from mcpx.config import`, `from mcpx.models import`

**Pattern examples:**
```python
# src/mcpx/cli.py (lines 1-18)
import argparse
import os
import re
import shutil
import sys

from mcpx import __version__
from mcpx.config import (
    add_server_to_config,
    get_config_path,
    load_config,
    remove_server_from_config,
)
from mcpx.models import MCPServer
from mcpx.init import cmd_init
from mcpx.sync import sync_all
from mcpx.utils import validate_server
```

**Path Aliases:**
- No path aliases configured. All imports use absolute paths from package root `mcpx`

## Error Handling

**Pattern:**
- Specific exception types caught and handled distinctly
- FileNotFoundError for missing files/config
- ValueError for invalid data/configuration
- json.JSONDecodeError for JSON parsing errors
- Exception catch-all as last resort with descriptive error messages

**Example from `src/mcpx/cli.py` (lines 129-136):**
```python
try:
    # operation here
except FileNotFoundError as e:
    print(f"Error: {e}")
    return EXIT_CONFIG_ERROR
except Exception as e:
    print(f"Fatal error: {e}")
    return EXIT_FATAL
```

**Validation Error Return:**
- Functions return tuple of (bool, str) for health checks: `health_check_stdio_server() -> tuple[bool, str]`
- Functions return None or ValidationError for validation: `validate_command_exists() -> ValidationError | None`
- Functions return lists of errors for comprehensive validation: `validate_server() -> list[ValidationError]`

## Logging

**Framework:** console printing via `print()` (no logging framework)

**Patterns:**
- User-facing messages printed to stdout: `print(f"mcpx sync v{__version__}")`
- Error messages printed to stdout with context: `print(f"Error: {e}")`
- Progress indicators use consistent formatting: `print("  ✓ command found")` and `print("  ✗ command not found")`
- Multi-line messages built with f-strings

**Example from `src/mcpx/cli.py` (lines 38-68):**
```python
print(f"mcpx sync v{__version__}")
print(f"Loading config from {config_path}")
server_count = len(config.servers)
server_names = ", ".join(config.servers.keys())
print(f"Found {server_count} MCP server(s): {server_names}")
print()
```

## Comments

**When to Comment:**
- All module docstrings: `# ABOUTME: [Purpose description]` - see examples below
- Function docstrings with ABOUTME: lines explaining business logic
- Complex regex patterns: `r'\$\{([A-Z_][A-Z0-9_]*)\}'` used for environment variable matching
- Non-obvious logic: why something is done a certain way

**ABOUTME Pattern:**
- Every file starts with file purpose comment using ABOUTME prefix
- Within functions, ABOUTME comments explain key business logic
- Examples:
  - `src/mcpx/cli.py` line 20-21: "Exit codes per spec" and definitions
  - `src/mcpx/cli.py` line 31-33: function responsibilities explained
  - `src/mcpx/config.py` line 1: file purpose
  - `src/mcpx/models.py` line 11-13: dataclass design rationale

**JSDoc/TSDoc:**
- Uses Python docstrings (Google style) for all public functions and classes
- Three-quote format with summary, detailed description, Args, Returns, Raises
- Example from `src/mcpx/config.py` (lines 44-62):
```python
def load_config(path: Path) -> Config:
    """Load and parse mcpx config from JSON file.

    ABOUTME: Uses built-in json module for JSON parsing
    ABOUTME: Fail-fast on parse errors with clear error messages
    ABOUTME: Expands environment variables in all string values
    ABOUTME: Supports both stdio and HTTP server types

    Args:
        path: Path to config.json file

    Returns:
        Parsed Config object

    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If JSON syntax is invalid
        ValueError: If required fields are missing or invalid
    """
```

## Function Design

**Size:**
- Range from 10-80 lines
- Smaller, focused functions preferred
- Examples:
  - `validate_command_exists()`: ~15 lines (single responsibility)
  - `cmd_sync()`: ~110 lines (main orchestrator, justified)
  - `validate_server()`: ~105 lines (comprehensive validation, justified)

**Parameters:**
- Type hints required on all parameters
- Default values used for optional parameters: `timeout: int | None = None`
- **kwargs avoided; explicit named parameters preferred
- Single parameter typically, up to 3-4 for complex functions

**Return Values:**
- Always type-hinted: `-> int`, `-> Config`, `-> list[ValidationError]`, `-> tuple[bool, str]`
- None used for optional returns: `ValidationError | None`
- Union types for multi-type returns: `tuple[bool, str]`
- Single return type preferred over multiple return types

## Module Design

**Exports:**
- Each module has clear public interface
- No star imports in codebase: all imports are explicit
- Modules organized by concern: config, models, sync, utils, platforms

**Examples:**
- `src/mcpx/config.py`: all config-related operations (load, save, add, remove)
- `src/mcpx/utils/validation.py`: all validation operations
- `src/mcpx/platforms/`: platform-specific adapters follow PlatformAdapter protocol

**Frozen Dataclasses:**
- MCPServer uses frozen dataclass (`@dataclass(frozen=True)`) to prevent accidental mutation (line 7-8)
- ValidationError uses frozen dataclass for immutability (line 22)
- Rationale: configuration objects should not change after creation

---

*Convention analysis: 2026-01-26*
