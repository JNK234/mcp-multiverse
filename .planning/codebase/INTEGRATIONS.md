# External Integrations

**Analysis Date:** 2026-01-26

## APIs & External Services

**MCP (Model Context Protocol) Servers:**
- Multiple MCP server types supported (stdio and HTTP)
- Discovery: Health checks validate servers before sync
- Platforms: Supports 6 AI coding assistant platforms as integration targets

**HTTP MCP Servers:**
- Integration mechanism: Custom HTTP POST requests with JSON-RPC protocol
- Implementation: `src/mcpx/utils/validation.py:health_check_http_server()`
- Headers support: Custom headers with environment variable expansion
- Protocol: JSON-RPC 2.0 with MCP initialize request
- Client ID: mcpx v0.1.0
- Timeout: 5 second default health check timeout

**Stdio MCP Servers:**
- Integration mechanism: Process spawning with stdin/stdout communication
- Implementation: `src/mcpx/utils/validation.py:health_check_stdio_server()`
- Protocol: JSON-RPC 2.0 newline-delimited over stdin/stdout
- Timeout: 5 second default health check timeout

## Data Storage

**Configuration Storage:**
- Master config file: `~/.mcpx/config.json` (JSON format)
- Source: `src/mcpx/config.py` handles all JSON I/O
- Structure: Stores 19+ MCP server definitions per user session

**Platform Integrations (Configuration Targets):**

| Platform | Config Location | Format | Adapter |
|----------|-----------------|--------|---------|
| Claude Code | `~/.claude.json` | JSON | `src/mcpx/platforms/claude.py:ClaudeAdapter` |
| Gemini CLI | `~/.gemini/settings.json` | JSON | `src/mcpx/platforms/gemini.py:GeminiAdapter` |
| Codex CLI | `~/.codex/config.toml` | TOML | `src/mcpx/platforms/codex.py:CodexAdapter` |
| Cline (VS Code) | `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json` | JSON | `src/mcpx/platforms/cline.py:ClineAdapter` |
| Roo Code (VS Code) | `~/Library/Application Support/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json` | JSON | `src/mcpx/platforms/roo.py:RooAdapter` |
| Kilo Code (VS Code) | `~/Library/Application Support/Code/User/globalStorage/kilocode.kilo-code/settings/mcp_settings.json` | JSON | `src/mcpx/platforms/kilo.py:KiloAdapter` |

**File Storage:**
- Backup system: `~/.mcpx/backups/` stores timestamped config backups
- Format: `{platform}_{YYYYMMDD}_{HHMMSS}.{ext}`
- Retention: Last 5 backups per platform automatically cleaned up
- Implementation: `src/mcpx/utils/backup.py:create_backup()`, `cleanup_old_backups()`

**Local Storage Only:**
- No cloud storage integration
- No remote database
- Filesystem-only caching (backups)

## Authentication & Identity

**Auth Provider:**
- Custom/None - No centralized authentication
- Platform-level: Each AI platform has its own auth (handled outside mcpx scope)

**Environment Variable Handling:**
- Expansion: `${VAR_NAME}` references in config expand to environment variables
- Use case: Secrets like API keys, tokens stored in shell environment, referenced in config
- Syntax: `${VAR_NAME}` required (uppercase, underscores)
- Fallback: Keeps original placeholder if variable unset (with warning)
- Implementation: `src/mcpx/utils/env.py:expand_env_vars()`

**Secrets Management:**
- No built-in secret storage
- Relies on environment variables set in shell profile (`~/.zshrc`, `~/.bashrc`)
- Example: `export GITHUB_TOKEN=actual-token` then reference as `${GITHUB_TOKEN}` in config

## Monitoring & Observability

**Error Tracking:**
- None (no external error tracking)
- Local error reporting via CLI exit codes (0=success, 1=partial, 2=config error, 3=fatal)

**Logs:**
- Console output only - structured text output to stdout
- Optional verbose flag: `mcpx sync --verbose` for detailed progress
- Health check results shown inline
- No file logging, no structured logging

**Health Check Reporting:**
- Inline reporting during sync
- Failed servers tagged with reason and skipped from sync
- Detailed error messages returned to caller

## CI/CD & Deployment

**Hosting:**
- Self-contained CLI tool - no server component
- Runs locally on user machines
- No cloud infrastructure required

**CI Pipeline:**
- Local testing: `uv run pytest` command in README
- Type checking: `uv run mypy src/mcpx --strict`
- Linting: `uv run ruff check src tests`
- No GitHub Actions workflow detected in codebase
- Coverage tracked locally via pytest-cov

**Distribution:**
- Python package distributed via PyPI
- Installation: `pip install mcpx` or `uv pip install mcpx`

## Environment Configuration

**Required env vars:**
- None globally required
- Application-specific: Set as needed by individual MCP servers
- Examples: `GITHUB_TOKEN`, `BRAVE_API_KEY`, `GITHUB_PERSONAL_ACCESS_TOKEN`

**Optional env vars:**
- `HOME` - User home directory (stdlib PathLib.home() uses this)
- Platform environment variables - Passed through to MCP subprocess servers

**Secrets location:**
- Shell profile files: `~/.zshrc`, `~/.bashrc`, or equivalent
- Export syntax: `export VAR_NAME=value`
- Referenced in config via `${VAR_NAME}` syntax

## Webhooks & Callbacks

**Incoming:**
- None - CLI tool, no server listening for incoming requests

**Outgoing:**
- None - No outbound webhooks to external services
- Integration type: Pull only (reads existing platform configs, writes merged configs)

## Platform Synchronization

**Sync Direction:**
- Bidirectional merge: Reads from all platforms, merges, writes back to all
- Merge strategy: Newest-wins on conflicts (by modification timestamp)
- Orphan preservation: Servers not in master config kept in platform configs

**Sync Flow:**
1. Load configs from all detected platforms
2. Merge into master config with deduplication
3. Validate all servers (command checks, URL checks, env var checks)
4. Create timestamped backups of existing platform configs
5. Save merged config to each platform in platform-specific format
6. Report results with per-platform server counts

**Health Validation:**
- Stdio servers: Verify command exists, spawn process, send MCP initialize, wait for response
- HTTP servers: POST JSON-RPC initialize to URL, validate 2xx response + JSON-RPC format
- Network: Uses `urllib.request.urlopen()` for HTTP checks (stdlib, no external deps)
- Command lookup: `shutil.which()` for PATH resolution (cross-platform)

---

*Integration audit: 2026-01-26*
