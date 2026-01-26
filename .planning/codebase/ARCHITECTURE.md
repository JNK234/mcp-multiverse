# Architecture

**Analysis Date:** 2026-01-26

## Pattern Overview

**Overall:** Adapter Pattern with Hub-and-Spoke Multi-Platform Sync

**Key Characteristics:**
- Protocol-based polymorphism for platform adapters
- Single source of truth (mcpx config) syncs to multiple destination platforms
- Fail-safe sync with orphan preservation (servers not in managed config are retained)
- Immutable config model with frozen dataclasses
- Lazy platform instantiation and detection

## Layers

**Data Model Layer:**
- Purpose: Define core immutable configuration structures
- Location: `src/mcpx/models.py`
- Contains: `MCPServer` (frozen dataclass), `Config` dataclass, `PlatformAdapter` protocol
- Depends on: Python stdlib (dataclasses, typing)
- Used by: All other layers

**Configuration Layer:**
- Purpose: Load/parse/save mcpx global config from JSON files
- Location: `src/mcpx/config.py`
- Contains: Config file I/O, environment variable expansion, server CRUD operations
- Depends on: `models.py`, `utils/env.py`, `platforms/base.py` (dict conversion)
- Used by: CLI, sync orchestration

**Platform Adapter Layer:**
- Purpose: Translate between mcpx format and platform-specific config formats
- Location: `src/mcpx/platforms/*.py` (one file per platform)
- Contains: `ClaudeAdapter`, `GeminiAdapter`, `CodexAdapter`, `ClineAdapter`, `RooAdapter`, `KiloAdapter`
- Depends on: `models.py`, `platforms/base.py` (shared utilities)
- Used by: Sync orchestration

**Utility Layer:**
- Purpose: Cross-cutting concerns (validation, backups, environment variables)
- Location: `src/mcpx/utils/*.py`
- Contains:
  - `validation.py` - Server health checks and command existence validation
  - `backup.py` - Config file backup management (max 5 backups per platform)
  - `env.py` - Environment variable expansion for `${VAR}` syntax
  - `toml_writer.py` - TOML-specific serialization for platforms that use it
- Depends on: Python stdlib + optional (toml reading)
- Used by: Configuration, sync, platform adapters

**CLI/Orchestration Layer:**
- Purpose: Command dispatch, user interaction, sync coordination
- Location: `src/mcpx/cli.py`, `src/mcpx/sync.py`, `src/mcpx/init.py`
- Contains: Command handlers (sync, list, add, remove, init), first-run detection
- Depends on: All lower layers
- Used by: Entry point (`__main__.py`)

## Data Flow

**Sync Operation:**

1. CLI loads config from `~/.mcpx/config.json` via `load_config()`
2. Validates all servers (fail-fast on config errors)
3. Iterates through all platform adapters (`get_all_platforms()`)
4. For each platform:
   - Loads existing config via `adapter.load()`
   - Creates backup of original file
   - Merges managed servers with orphan servers
   - Saves merged servers via `adapter.save()`
   - Records result in report
5. Prints summary report and returns exit code

**First-Run Initialization:**

1. Detects all installed platforms (check config path existence)
2. Loads existing servers from each platform
3. Deduplicates servers by name across all platforms
4. Generates `~/.mcpx/config.json` with deduplicated set
5. Returns discovery report

**Server Addition/Removal:**

1. Load existing config via `load_config()`
2. Mutate servers dict (create new dict, immutable MCPServer objects)
3. Save updated config via `save_config()`

**State Management:**
- Global state: `~/.mcpx/config.json` (JSON file on disk)
- Platform state: Per-platform config files (JSON, TOML, VS Code settings)
- No in-memory state between commands (stateless CLI design)
- Backups stored in `~/.mcpx/backups/[platform]/` with timestamp-based naming

## Key Abstractions

**MCPServer:**
- Purpose: Represent a single MCP server configuration in platform-agnostic form
- Examples: `src/mcpx/models.py` (dataclass definition)
- Pattern: Frozen dataclass prevents accidental mutations; supports both stdio and HTTP types

**PlatformAdapter (Protocol):**
- Purpose: Define contract all platform-specific adapters must implement
- Examples: `src/mcpx/platforms/claude.py`, `src/mcpx/platforms/gemini.py`, etc.
- Pattern: Runtime-checkable protocol enables duck typing; each adapter implements `load()`, `save()`, `save_project()` methods

**Config:**
- Purpose: Hold loaded mcpx configuration (version + servers dict)
- Examples: `src/mcpx/models.py` (dataclass definition)
- Pattern: Simple container; no methods (all logic in config.py module functions)

**Server Type Detection:**
- Purpose: Auto-detect stdio vs HTTP based on presence of `url` vs `command` field
- Examples: `src/mcpx/platforms/base.py` (dict_to_server function)
- Pattern: Explicit `type` field in config overrides auto-detection; useful for backwards compatibility

## Entry Points

**CLI Entry Point:**
- Location: `src/mcpx/__main__.py`
- Triggers: `python -m mcpx` or installed `mcpx` command
- Responsibilities: Parse args, dispatch to command handler

**Command Handlers:**
- `cmd_sync()` in `src/mcpx/cli.py`: Sync command orchestration
- `cmd_list()` in `src/mcpx/cli.py`: List servers in config
- `cmd_add()` in `src/mcpx/cli.py`: Add server to config
- `cmd_remove()` in `src/mcpx/cli.py`: Remove server from config
- `cmd_init()` in `src/mcpx/cli.py`: Project-level MCP setup

**Sync Entry Point:**
- Function: `sync_all()` in `src/mcpx/sync.py`
- Called by: `cmd_sync()` in CLI
- Returns: `SyncReport` with per-platform results

## Error Handling

**Strategy:** Fail-fast on config errors, fail-graceful on platform errors

**Patterns:**

1. **Config Validation (Fail-Fast):**
   - All servers validated before sync begins
   - First validation error causes entire sync to abort
   - Example: `validate_server()` in `src/mcpx/utils/validation.py` checks command existence

2. **Platform Errors (Fail-Graceful):**
   - Platform adapter exceptions are caught, recorded, but don't stop other platforms
   - Each platform sync is wrapped in try-except
   - Errors logged in `SyncReport.errors` list
   - Example: `src/mcpx/sync.py` lines 158-161

3. **Validation Errors (Data Structure):**
   - `ValidationError` dataclass in `src/mcpx/utils/validation.py` holds severity + message
   - Server validation returns list of errors (severity "error" or "warning")
   - Errors printed to user; warnings are non-blocking

4. **Config Parsing Errors:**
   - JSON parse failures raise `json.JSONDecodeError`
   - Missing required fields raise `ValueError`
   - Missing config file raises `FileNotFoundError`
   - All propagate up to CLI handler

## Cross-Cutting Concerns

**Logging:**
- No centralized logger; all output via `print()` statements
- Each command prints status messages to stdout
- Errors printed to stdout (not stderr)
- Example: `src/mcpx/cli.py` lines 38-127

**Validation:**
- Server command existence checked before sync via `validate_command_exists()`
- HTTP servers health-checked via `health_check_http_server()` (optional timeout)
- Stdio servers tested via `health_check_stdio_server()` (spawn and timeout)
- All validation functions in `src/mcpx/utils/validation.py`

**Environment Variable Expansion:**
- Pattern: `${VAR_NAME}` syntax in config values
- Expanded after config parsing, before use
- Supports nested expansion (e.g., `${HOME}/path`)
- Location: `src/mcpx/utils/env.py` (expand_env_vars function)

**Backup Management:**
- Automatic backup created before each sync
- Location: `~/.mcpx/backups/[platform_name]/[timestamp].json` or `.toml`
- Retention: Last 5 backups per platform kept
- Location: `src/mcpx/utils/backup.py` (create_backup, manage_backup_retention functions)

---

*Architecture analysis: 2026-01-26*
