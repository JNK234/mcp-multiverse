# Codebase Structure

**Analysis Date:** 2026-01-26

## Directory Layout

```
mcp-multiverse/
├── src/mcpx/               # Main package
│   ├── __init__.py         # Version, exports
│   ├── __main__.py         # CLI entry point
│   ├── cli.py              # Command handlers
│   ├── config.py           # Config loading/saving
│   ├── init.py             # Project-level init
│   ├── models.py           # Data structures
│   ├── sync.py             # Sync orchestration
│   ├── platforms/          # Platform adapters
│   │   ├── __init__.py     # Registry and factory
│   │   ├── base.py         # Shared utilities
│   │   ├── claude.py       # Claude Code adapter
│   │   ├── cline.py        # Cline (VS Code) adapter
│   │   ├── codex.py        # Codex CLI adapter
│   │   ├── gemini.py       # Gemini CLI adapter
│   │   ├── kilo.py         # Kilo Code adapter
│   │   └── roo.py          # Roo Code adapter
│   └── utils/              # Shared utilities
│       ├── __init__.py     # Exports
│       ├── backup.py       # Backup management
│       ├── env.py          # Environment variable expansion
│       ├── toml_writer.py  # TOML serialization
│       └── validation.py   # Server validation & health checks
├── tests/                  # Test suite
│   ├── conftest.py         # Pytest fixtures
│   ├── fixtures/           # Test data
│   ├── test_platforms/     # Platform adapter tests
│   ├── test_*.py           # Unit tests
│   └── test_cli_*.py       # CLI command tests
├── pyproject.toml          # Project metadata, dependencies
├── README.md               # User documentation
└── .mcpx.json              # Initial state file (usually empty)
```

## Directory Purposes

**`src/mcpx/`:**
- Purpose: Main package code
- Contains: Core logic for config management, sync, CLI
- Key files: `cli.py` (commands), `sync.py` (orchestration), `models.py` (data structures)

**`src/mcpx/platforms/`:**
- Purpose: Platform-specific configuration adapters
- Contains: One adapter class per supported platform
- Key files: `base.py` (shared utilities), `__init__.py` (registry)
- Pattern: Each adapter implements the `PlatformAdapter` protocol

**`src/mcpx/utils/`:**
- Purpose: Cross-cutting utilities
- Contains: Validation, backups, environment variables, TOML writing
- Key files: `validation.py` (health checks), `backup.py` (retention logic), `env.py` (variable expansion)

**`tests/`:**
- Purpose: Unit and integration tests
- Contains: Test cases for each major component
- Key patterns: Pytest fixtures in `conftest.py`, per-platform tests in `test_platforms/`

## Key File Locations

**Entry Points:**
- `src/mcpx/__main__.py`: Python module entry point (`python -m mcpx`)
- `src/mcpx/cli.py`: Command handler functions; entry point is `main()` function
- `pyproject.toml` line 32: Defines CLI script entry point as `mcpx = "mcpx.cli:main"`

**Configuration:**
- `pyproject.toml`: Project metadata, dependencies, tool config (ruff, mypy, pytest)
- `src/mcpx/config.py`: Config file I/O (load_config, save_config, add_server_to_config, remove_server_from_config)
- `src/mcpx/models.py`: Data classes (MCPServer, Config, PlatformAdapter protocol)

**Core Logic:**
- `src/mcpx/sync.py`: Sync orchestration (sync_all, merge_servers functions; SyncReport dataclass)
- `src/mcpx/cli.py`: Command dispatch (cmd_sync, cmd_list, cmd_add, cmd_remove, cmd_init functions)
- `src/mcpx/init.py`: Project-level setup (interactive_select function for multi-select UI)

**Platforms:**
- `src/mcpx/platforms/__init__.py`: Platform registry (ALL_PLATFORMS list, get_all_platforms factory)
- `src/mcpx/platforms/base.py`: Shared conversion functions (dict_to_server, server_to_dict, read_json_file, write_json_file)
- `src/mcpx/platforms/claude.py`: Claude Code adapter
- `src/mcpx/platforms/gemini.py`: Gemini CLI adapter
- `src/mcpx/platforms/codex.py`: Codex CLI adapter
- `src/mcpx/platforms/cline.py`: Cline VS Code adapter
- `src/mcpx/platforms/roo.py`: Roo Code adapter
- `src/mcpx/platforms/kilo.py`: Kilo Code adapter

**Utilities:**
- `src/mcpx/utils/validation.py`: validate_server, validate_command_exists, health_check_stdio_server, health_check_http_server
- `src/mcpx/utils/backup.py`: create_backup, get_backup_dir, manage_backup_retention
- `src/mcpx/utils/env.py`: expand_env_vars function
- `src/mcpx/utils/toml_writer.py`: TOML serialization for Codex CLI

**Testing:**
- `tests/conftest.py`: Pytest fixtures (temporary directories, mock platforms, sample configs)
- `tests/test_platforms/test_*.py`: Platform adapter tests (one file per platform)
- `tests/test_cli_*.py`: CLI command integration tests
- `tests/test_sync.py`: Sync orchestration tests
- `tests/test_config.py`: Config loading/saving tests
- `tests/test_*.py`: Unit tests for utilities, models, validation

## Naming Conventions

**Files:**
- Python modules: `lowercase_with_underscores.py` (e.g., `validate_server`, `backup_manager`)
- Platform adapters: `[platform_name].py` (e.g., `claude.py`, `gemini.py`)
- Test files: `test_[module_name].py` (e.g., `test_config.py`)
- Platform tests: `test_platforms/test_[platform_name].py` (e.g., `test_platforms/test_claude.py`)

**Directories:**
- Package dirs: `lowercase_with_underscores` (e.g., `platforms`, `utils`)
- Subdirectories follow module purpose (e.g., `test_platforms/` for platform-specific tests)

**Functions:**
- Regular functions: `snake_case` (e.g., `validate_server`, `sync_all`)
- Command handlers: `cmd_[command_name]` (e.g., `cmd_sync`, `cmd_add`)
- Private functions: No leading underscore convention (all functions in private modules)

**Classes:**
- Platform adapters: `[PlatformName]Adapter` (e.g., `ClaudeAdapter`, `GeminiAdapter`)
- Data classes: `PascalCase` (e.g., `Config`, `MCPServer`, `SyncReport`)
- Protocol classes: `PascalCase` (e.g., `PlatformAdapter`)

**Constants:**
- Exit codes: `EXIT_[NAME]` (e.g., `EXIT_SUCCESS`, `EXIT_CONFIG_ERROR`)
- ANSI color codes: `UPPERCASE` (e.g., `BOLD`, `GREEN`, `CYAN`)
- Config paths: `UPPERCASE` (e.g., `CONFIG_DIR`, `CONFIG_FILE`)

## Where to Add New Code

**New Platform Support:**
- Create: `src/mcpx/platforms/[platform_name].py`
- Implement: Class `[PlatformName]Adapter` implementing `PlatformAdapter` protocol
- Register: Add to `ALL_PLATFORMS` list in `src/mcpx/platforms/__init__.py`
- Test: Create `tests/test_platforms/test_[platform_name].py` with tests following pattern of existing adapters

**New Utility Function:**
- If validation/health check: Add to `src/mcpx/utils/validation.py`
- If backup-related: Add to `src/mcpx/utils/backup.py`
- If environment-related: Add to `src/mcpx/utils/env.py`
- If format-specific (TOML): Add to `src/mcpx/utils/toml_writer.py`
- Export from `src/mcpx/utils/__init__.py`

**New CLI Command:**
- Handler function: Add `cmd_[command_name]()` in `src/mcpx/cli.py`
- Argument parsing: Add subparser in `main()` function, line ~280
- Exit codes: Use defined `EXIT_*` constants (SUCCESS, PARTIAL, CONFIG_ERROR, FATAL)
- Tests: Add `tests/test_cli_[command_name].py` or update existing CLI test file

**New Server Type Support:**
- Modify: `MCPServer` dataclass in `src/mcpx/models.py` (add type literal option)
- Modify: `dict_to_server()` in `src/mcpx/platforms/base.py` (handle new type)
- Modify: `server_to_dict()` in `src/mcpx/platforms/base.py` (serialize new fields)
- Update: All platform adapters if they need special handling (usually automatic via server_to_dict)

## Special Directories

**`~/.mcpx/`:**
- Purpose: User's mcpx configuration directory
- Contains: `config.json` (main config), `backups/` (per-platform backups)
- Generated: On first run
- Committed: No (user configuration, not in repo)

**`~/.mcpx/backups/`:**
- Purpose: Backup storage per platform
- Structure: `[platform_name]/[timestamp].json` or `.toml`
- Rotation: Keeps last 5 backups per platform (managed by `manage_backup_retention()`)
- Generated: Automatically during sync
- Committed: No (user data, not in repo)

**`.planning/codebase/`:**
- Purpose: GSD codebase analysis documents
- Contains: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, STACK.md, INTEGRATIONS.md, CONCERNS.md
- Generated: By GSD mapper commands
- Committed: Yes (development reference)

---

*Structure analysis: 2026-01-26*
