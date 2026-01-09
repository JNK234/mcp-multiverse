# mcpx

Universal MCP server sync manager for AI coding assistants.

## Overview

mcpx synchronizes MCP (Model Context Protocol) server configurations across multiple AI coding assistants from a single source of truth. Define your MCP servers once in `~/.mcpx/config.toml`, and mcpx handles syncing to all your AI tools automatically.

### Supported Platforms

- **Claude Code** (`~/.claude/claude_desktop_config.json`)
- **Gemini CLI** (`~/.gemini/settings.json`)
- **Cline** (VS Code extension settings)
- **Roo Code** (VS Code extension settings)
- **Kilo Code** (VS Code extension settings)
- **OpenAI Codex** (`~/.codex/config.toml`)

## Installation

```bash
pip install mcpx
```

Or install with uv:

```bash
uv pip install mcpx
```

## Quick Start

### First Run: Auto-Detect Existing Servers

```bash
mcpx sync
```

On first run, mcpx will:
1. Scan all platforms for existing MCP servers
2. Deduplicate servers by name
3. Generate `~/.mcpx/config.toml`
4. Ask you to review and customize the config
5. Sync to all platforms on next run

### Manual Configuration

1. Create `~/.mcpx/config.toml`:

```toml
# mcpx configuration

[servers."filesystem"]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/Users/john/projects"]

[servers."github"]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { GITHUB_PERSONAL_ACCESS_TOKEN = "ghp_xxxx" }
```

2. Sync to all platforms:

```bash
mcpx sync
```

## Configuration

### Global Config Location

`~/.mcpx/config.toml` (created automatically on first run)

### Server Definition Format

Each server has:
- `command`: Command to run (e.g., `npx`, `node`, `python`)
- `args`: List of command arguments (optional)
- `env`: Dictionary of environment variables (optional)

### Example Configurations

**Simple server (no args, no env):**

```toml
[servers."brave-search"]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-brave-search"]
```

**Server with environment variables:**

```toml
[servers."github"]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
[servers."github".env]
GITHUB_PERSONAL_ACCESS_TOKEN = "ghp_xxxx"
GITHUB_REPOS = "myorg/*"
```

**Local Python server:**

```toml
[servers."local-tools"]
command = "uvx"
args = ["my-mcp-server"]
env = { API_KEY = "secret123" }
```

### Environment Variable Expansion

Use `${VAR_NAME}` syntax in commands and args:

```toml
[servers."my-server"]
command = "${HOME}/.local/bin/my-server"
args = ["--api-key", "${API_KEY}"]
```

Variables are expanded from your shell environment at sync time.

## Commands

### `mcpx sync` - Sync to All Platforms

Sync your global config to all platforms:

```bash
mcpx sync
```

**What it does:**
1. Validates server commands exist
2. Creates backups of existing configs
3. Merges with orphan servers (servers in platforms but not in mcpx)
4. Writes to all platform configs
5. Reports success/failure per platform

**Exit codes:**
- `0` = Success (all platforms synced)
- `1` = Partial success (some platforms failed)
- `2` = Config error (validation failed)
- `3` = Fatal error

### `mcpx init` - Initialize Project-Level MCPs

Interactive project-level MCP selection (for supported platforms):

```bash
mcpx init
```

**What it does:**
1. Loads global config
2. Presents interactive multi-select UI
3. Creates `.mcpx.toml` in your project
4. Syncs to project-level configs:
   - Claude Code: `.mcp.json`
   - Roo Code: `.roo/mcp.json`
   - Kilo Code: `.kilocode/mcp.json`

### `mcpx list` - List All MCPs

Show all servers in your config:

```bash
mcpx list
```

**Example output:**

```
mcpx list v0.1.0

MCP Servers in /Users/john/.mcpx/config.toml:

  filesystem
    command: npx
    args: -y @modelcontextprotocol/server-filesystem /Users/john/projects

  github
    command: npx
    args: -y @modelcontextprotocol/server-github
    env: GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxx
```

### `mcpx validate` - Validate Config

Check your config without syncing:

```bash
mcpx validate
```

**Checks:**
- TOML syntax validity
- Required fields present
- Commands exist on PATH
- Environment variables set

**Example output:**

```
mcpx validate v0.1.0

Validating config...
  ✓ TOML syntax valid
  ✓ 2 server(s) defined

Checking commands...
  ✓ npx found
  ✓ python3 found

Environment variable warnings:
  ⚠ Warning: API_KEY not set (used in server 'my-server')

Config valid! Ready to sync.
```

### `mcpx --version` - Show Version

```bash
mcpx --version
# Output: mcpx v0.1.0
```

### `mcpx --help` - Show Help

```bash
mcpx --help
mcpx sync --help
mcpx init --help
mcpx list --help
mcpx validate --help
```

## Project-Level Configuration

For projects that need specific MCPs, use `mcpx init`:

```bash
cd /path/to/my-project
mcpx init
```

This creates `.mcpx.toml`:

```toml
# Project-level MCP configuration
[mcpx]
version = "1.0"
servers = ["filesystem", "github"]
```

And syncs to:
- `.mcp.json` (Claude Code)
- `.roo/mcp.json` (Roo Code)
- `.kilocode/mcp.json` (Kilo Code)

## Platform-Specific Details

### Claude Code

- **Global config:** `~/.claude/claude_desktop_config.json`
- **Project config:** `.mcp.json` in project root
- **Format:** JSON with `mcpServers` key

### Gemini CLI

- **Global config:** `~/.gemini/settings.json`
- **Project config:** Not supported
- **Format:** JSON with `mcpServers` key
- **Preserves:** Other settings like `selectedAuthType`, `theme`

### Cline (VS Code)

- **Global config:** VS Code `settings.json`
- **Project config:** Not supported
- **Format:** JSON with `mcpServers` key
- **Adds:** `disabled: false`, `alwaysAllow: []` defaults

### Roo Code (VS Code)

- **Global config:** VS Code `settings.json`
- **Project config:** `.roo/mcp.json`
- **Format:** JSON with `mcpServers` key
- **Adds:** `disabled: false`, `alwaysAllow: []` defaults

### Kilo Code (VS Code)

- **Global config:** VS Code `settings.json`
- **Project config:** `.kilocode/mcp.json`
- **Format:** JSON with `mcpServers` key
- **Adds:** `disabled: false`, `alwaysAllow: []` defaults

### OpenAI Codex

- **Global config:** `~/.codex/config.toml`
- **Project config:** Not supported
- **Format:** TOML with `mcp_servers` key (snake_case)

## Backup and Safety

### Automatic Backups

Every sync creates automatic backups in `~/.mcpx-backups/`:

```
~/.mcpx-backups/
├── claude_desktop_config_20250108_143022.json
├── settings_20250108_143022.json
└── ...
```

**Backup format:** `{filename}_{timestamp}.{ext}`

### Orphan Servers

mcpx preserves "orphan" servers - servers that exist in platform configs but aren't defined in your mcpx config. This prevents accidental data loss.

**Example:**
- mcpx config defines: `filesystem`, `github`
- Platform has: `filesystem`, `github`, `old-server`
- After sync: `filesystem`, `github`, `old-server` (old-server preserved)

### Validation

mcpx validates before syncing:
- Checks if commands exist on PATH
- Warns about unset environment variables
- Shows clear error messages with actionable fixes

## Troubleshooting

### "Command not found" Error

**Problem:** Server command doesn't exist on PATH.

**Solution:**
1. Install the required tool (e.g., `npm install -g npx`)
2. Use full path to command: `command = "/usr/local/bin/npx"`
3. Check command with: `mcpx validate`

### "Config file not found"

**Problem:** `~/.mcpx/config.toml` doesn't exist.

**Solution:** Run `mcpx sync` - it will auto-generate the config from existing platforms.

### "Permission denied" when writing config

**Problem:** No write access to platform config directory.

**Solution:**
1. Check directory permissions: `ls -la ~/.claude/`
2. Fix permissions: `chmod u+w ~/.claude/claude_desktop_config.json`
3. Or run with appropriate permissions

### Environment variables not expanding

**Problem:** `${VAR}` not replaced with actual value.

**Solution:**
1. Ensure variable is set in shell: `echo $MY_VAR`
2. Use correct syntax: `${VAR_NAME}` (not `$VAR_NAME`)
3. Export variable: `export MY_VAR=value`

### Platform-specific issues

**Claude Code not syncing:**
- Check Claude Desktop is running
- Verify config path: `ls -la ~/.claude/claude_desktop_config.json`

**Gemini CLI not syncing:**
- Check config exists: `ls -la ~/.gemini/settings.json`
- Verify JSON syntax: `python3 -m json.tool ~/.gemini/settings.json`

**VS Code extensions (Cline/Roo/Kilo) not syncing:**
- Check VS Code settings path
- Verify extension is installed
- Check for multiple VS Code instances (Insiders vs stable)

## Advanced Usage

### Sync from Specific Platform

Temporarily sync from a specific platform (one-time import):

```bash
# Not directly supported - use manual config instead
# Or copy servers from platform config to mcpx config
```

### Dry Run

Validate without making changes:

```bash
mcpx validate
```

### Verbose Output

Check logs for detailed sync information:

```bash
# Logs go to stdout
mcpx sync
```

## Development

### Running from Source

```bash
git clone https://github.com/yourusername/mcpx.git
cd mcpx
uv pip install -e .
mcpx --help
```

### Running Tests

```bash
uv run pytest
```

### Type Checking

```bash
uv run mypy src/mcpx --strict
```

### Linting

```bash
uv run ruff check src tests
```

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Links

- **Specification:** `.claude/spec/mcpx-specification.md`
- **Repository:** https://github.com/yourusername/mcpx
- **Issues:** https://github.com/yourusername/mcpx/issues

## Changelog

### v0.1.0 (2025-01-08)

- Initial release
- Support for 6 AI coding platforms
- Auto-detection of existing servers
- Project-level MCP configuration
- Comprehensive validation and error reporting
- Automatic backups before sync
