# Codebase Concerns

**Analysis Date:** 2026-01-26

## Tech Debt

**Large CLI Module:**
- Issue: `src/mcpx/cli.py` is 661 lines with multiple command handlers mixed together
- Files: `src/mcpx/cli.py`
- Impact: Difficult to test individual commands, high cyclomatic complexity in main function, terminal printing logic scattered throughout
- Fix approach: Extract command handlers into separate module (`src/mcpx/commands/`), separate terminal UI from logic, implement command interface pattern

**Duplicate JSON Serialization Logic:**
- Issue: Config saving duplicated in `sync.py:first_run_init()` and `config.py:save_config()`
- Files: `src/mcpx/sync.py` (lines 213-238), `src/mcpx/config.py` (lines 128-161)
- Impact: Server dict-to-JSON conversion logic appears in two places; changes require updating both locations
- Fix approach: Extract `_build_server_data()` utility function, reuse in both modules

**Regex Patterns Repeated:**
- Issue: Environment variable pattern `r'\$\{([A-Z_][A-Z0-9_]*)\}'` appears in 5+ locations
- Files: `src/mcpx/cli.py` (lines 250-285), `src/mcpx/utils/validation.py` (lines 139-200)
- Impact: Pattern changes require updating multiple locations; inconsistent if regex differs
- Fix approach: Define `ENV_VAR_PATTERN` constant in `src/mcpx/utils/validation.py`, import everywhere

**Exception Handling Too Broad:**
- Issue: `src/mcpx/cli.py` catches generic `Exception` in multiple places (lines 134, 314, 485, 545)
- Files: `src/mcpx/cli.py`
- Impact: Masks specific errors, makes debugging difficult, hides unexpected failures
- Fix approach: Catch specific exceptions (`ValueError`, `FileNotFoundError`, `OSError`) per command

## Known Bugs

**Environment Variable Expansion in Platform Adapters:**
- Issue: `src/mcpx/config.py` expands env vars after server creation (lines 89-107), but platform adapters don't perform expansion
- Symptoms: HTTP servers with `${API_KEY}` in URL may not expand when saved to platform configs
- Files: `src/mcpx/config.py`, `src/mcpx/platforms/base.py` (dict_to_server)
- Trigger: Add HTTP server with env var in URL, sync, load platform config directly
- Workaround: Ensure env vars are set before running mcpx

**Health Check Subprocess Cleanup Edge Case:**
- Issue: `src/mcpx/utils/validation.py:health_check_stdio_server()` (line 352) catches generic `Exception` in finally block, may hide cleanup errors
- Symptoms: Subprocess may not be properly terminated if unexpected error occurs
- Files: `src/mcpx/utils/validation.py` (lines 351-361)
- Trigger: Subprocess fails with unusual error during initialization
- Workaround: Manual process cleanup may be needed in rare cases

**No Validation of Server Name Conflicts:**
- Issue: `src/mcpx/config.py:add_server_to_config()` (line 186) silently overwrites if server.name already exists
- Symptoms: User adds server with same name as existing server, existing config silently replaced
- Files: `src/mcpx/config.py` (lines 165-189)
- Trigger: `mcpx add server_name` when server_name already in config
- Workaround: Check output message "Server 'x' already exists. It will be replaced." and cancel if needed

## Security Considerations

**Shell Command Injection in Stdio Servers:**
- Risk: `src/mcpx/cli.py:cmd_add()` (line 349) and `src/mcpx/config.py:load_config()` don't validate command arguments before execution
- Files: `src/mcpx/cli.py` (line 349), `src/mcpx/utils/validation.py` (line 249)
- Current mitigation: Commands are executed with `subprocess.Popen` which doesn't use shell=True, so args are passed as list (safer)
- Recommendations: Add validation that command exists before saving, sanitize args for special characters, document that mcpx does not support shell metacharacters in args

**HTTP Headers from User Input:**
- Risk: `src/mcpx/cli.py:cmd_add()` (lines 361-365) accepts custom headers from CLI input without validation
- Files: `src/mcpx/cli.py`
- Current mitigation: Headers are stored as-is in JSON, then used in urllib request (standard library validates headers)
- Recommendations: Validate header names follow RFC 7230, reject headers that could cause injection (Content-Length, Transfer-Encoding, etc.)

**Environment Variable Exposure:**
- Risk: `src/mcpx/utils/validation.py:health_check_stdio_server()` (line 252) copies os.environ to subprocess env
- Files: `src/mcpx/utils/validation.py` (lines 251-260)
- Current mitigation: subprocess.Popen spawns isolated process
- Recommendations: Document that health checks inherit parent process env vars, recommend not running mcpx with sensitive env vars exposed

**Backup Directory Permissions:**
- Risk: `src/mcpx/utils/backup.py:create_backup()` (line 52) creates backup_dir with default umask
- Files: `src/mcpx/utils/backup.py`
- Current mitigation: Backup files contain platform configs which may have sensitive data
- Recommendations: Set explicit permissions (0o700) on backup directory after creation

## Performance Bottlenecks

**Synchronous Platform Sync:**
- Problem: `src/mcpx/sync.py:sync_all()` (lines 132-162) loads, validates, syncs to each platform sequentially
- Files: `src/mcpx/sync.py`
- Cause: For loop iterates platforms one at a time; each backup/load/save is blocking I/O
- Improvement path: With 6+ platforms, could parallelize platform syncs using `concurrent.futures.ThreadPoolExecutor`, maintain backup creation for rollback

**Regex Matching Per Environment Variable:**
- Problem: `src/mcpx/utils/validation.py:validate_server()` (lines 150-157) searches entire string for each env var, new match for each var
- Files: `src/mcpx/utils/validation.py`
- Cause: Pattern matching done independently per field, no caching of results
- Improvement path: Compile regex once, scan all fields at initialization, cache results

**File I/O in CLI List Command:**
- Problem: `src/mcpx/cli.py:cmd_list()` (lines 139-192) loads entire config just to display servers
- Files: `src/mcpx/cli.py`
- Cause: Full JSON parse/validation even though only display needed
- Improvement path: Lazy loading - parse JSON without validation for list, only validate on sync

## Fragile Areas

**Platform Adapter Registry:**
- Files: `src/mcpx/platforms/__init__.py` (lines 11-18)
- Why fragile: New platform adapters must be manually added to `ALL_PLATFORMS` list and imported; easy to forget
- Safe modification: Add platform adapter, update `__all__`, add to ALL_PLATFORMS - follow existing pattern exactly
- Test coverage: `tests/test_sync.py` should test that all registered platforms are instantiable

**Config File Format Migration:**
- Files: `src/mcpx/config.py` (lines 69-79), `src/mcpx/models.py` (lines 31)
- Why fragile: Version field in config is not used or checked; format is hardcoded to "1.0"
- Safe modification: Any format changes require version bump logic in load_config(), migration path for existing configs
- Test coverage: Need tests for loading configs with different version numbers

**Terminal UI in init.py:**
- Files: `src/mcpx/init.py` (lines 18-100+)
- Why fragile: Uses raw termios/tty, escape sequences hardcoded, only works on Unix
- Safe modification: Platform-specific terminal handling needed before modifying, test on Windows
- Test coverage: Interactive mode tests currently missing; mock terminal input difficult

**Health Check JSON Parsing:**
- Files: `src/mcpx/utils/validation.py` (lines 314-341)
- Why fragile: Looks for first line starting with "{" to find JSON response (lines 305-309), assumes single-line JSON
- Safe modification: Could fail if server outputs non-JSON before response, or multi-line JSON
- Test coverage: `tests/test_health_check.py` mocks simple echo responses; need tests with verbose server output

## Scaling Limits

**Backup Directory Retention:**
- Current capacity: Keeps last 5 backups per platform (6 platforms = 30 max files)
- Limit: With daily syncs, backups per platform persist 5 days, after 30 days only latest per platform retained
- Scaling path: Make retention policy configurable in config.json, add `--backup-retention` CLI flag

**Platform Configuration Loading:**
- Current capacity: All 6 platform adapters instantiated and loaded on every sync
- Limit: Adding 10+ more platforms means 10+ file I/O operations per sync
- Scaling path: Lazy-load platforms (only instantiate requested platforms), cache platform config paths

**CLI Argument Parsing:**
- Current capacity: Single-line help text, simple argparse subcommands
- Limit: Adding 10+ new commands makes CLI management complex
- Scaling path: Plugin-based command system, each command in separate module

## Dependencies at Risk

**No Explicit Version Pinning in Code:**
- Risk: `pyproject.toml` specifies `tomli>=2.0.0` without upper bound
- Files: `pyproject.toml` (line 21)
- Impact: Major version bump in tomli (e.g., 3.0.0) could introduce breaking changes
- Migration plan: Pin `tomli>=2.0.0,<3.0.0`, review on next major release

**Python 3.12+ Only:**
- Risk: `requires-python = ">=3.12"` (pyproject.toml:7) limits adoption
- Files: `pyproject.toml`
- Impact: Users on Python 3.11 or earlier cannot install
- Migration plan: Consider dropping to 3.11 if no language features require 3.12, update min version in CI

## Missing Critical Features

**No Dry-Run Mode:**
- Problem: `mcpx sync` directly modifies platform configs with no --dry-run option
- Blocks: Users cannot preview what would change before syncing
- Fix approach: Add `--dry-run` flag to sync command, skip save_platform step, show diff instead

**No Rollback After Failed Sync:**
- Problem: If partial sync fails (some platforms succeed, others fail), no way to rollback to previous state
- Blocks: Recovering from sync failure requires manual restoration from backups
- Fix approach: Track which platforms succeeded, offer rollback command on exit, implement transactional sync

**No Global MCP Config Lock:**
- Problem: Running multiple `mcpx` commands concurrently could cause config corruption
- Blocks: CI/CD pipelines or parallel execution scenarios are unsafe
- Fix approach: Implement file locking in `load_config()`/`save_config()`, retry with exponential backoff

## Test Coverage Gaps

**Interactive Terminal UI Not Tested:**
- What's not tested: `src/mcpx/init.py:interactive_select()` (lines 18-100)
- Files: `src/mcpx/init.py`
- Risk: Terminal input handling, escape sequence parsing, selection state management are untested
- Priority: Medium - only used in `mcpx init` which is less critical than sync

**Platform Adapter Error Handling:**
- What's not tested: Exception handling in platform adapters when config files are malformed or unwritable
- Files: `src/mcpx/platforms/claude.py`, `src/mcpx/platforms/cline.py`, etc.
- Risk: Sync silently fails if platform config is unreadable, errors caught but not surfaced clearly
- Priority: High - sync failures must be visible

**Health Check Timeout Edge Cases:**
- What's not tested: Behavior when subprocess hangs beyond timeout, when stderr output is very large
- Files: `src/mcpx/utils/validation.py:health_check_stdio_server()`
- Risk: Timeout handling may not work as expected with slow servers
- Priority: Low - health check is optional feature

**Config File Encoding Issues:**
- What's not tested: Loading config files with non-UTF-8 encoding, files with BOM markers
- Files: `src/mcpx/config.py:load_config()` (line 66)
- Risk: JSONDecodeError will be raised rather than graceful handling
- Priority: Low - UTF-8 is standard, but could affect non-English systems

---

*Concerns audit: 2026-01-26*
