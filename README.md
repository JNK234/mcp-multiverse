# mcpx

Universal MCP server sync manager for AI coding assistants.

## Overview

mcpx synchronizes MCP (Model Context Protocol) server configurations across multiple AI coding assistants from a single source of truth. Define your MCP servers once in `~/.mcpx/config.json`, and mcpx handles syncing to all your AI tools automatically.

### Key Features

- **One config, all platforms**: Edit once, sync everywhere
- **Bidirectional merge**: Auto-imports existing configs with newest-wins conflict resolution
- **Health validation**: Servers are health-checked before sync (skip broken MCPs)
- **Project-level control**: Load only the MCPs you need per project
- **Backup retention**: Automatic backups with last 5 kept per platform
- **Stdio and HTTP servers**: Support for both command-based and URL-based MCP servers

### Supported Platforms

| Platform | Global Config | Project Config | Status |
|----------|---------------|----------------|--------|
| Claude Code | `~/.claude.json` | `.mcp.json` | Full |
| Gemini CLI | `~/.gemini/settings.json` | Not supported | Global only |
| Codex CLI | `~/.codex/config.toml` | Not supported | Global only |
| Cline (VS Code) | VS Code settings | Not supported | Global only |
| Roo Code (VS Code) | VS Code settings | `.roo/mcp.json` | Full |
| Kilo Code (VS Code) | VS Code settings | `.kilocode/mcp.json` | Full |

## Installation

```bash
pip install mcpx
```

Or install with uv:

```bash
uv pip install mcpx
```

## Quick Start

### First Run: Auto-Import Existing Servers

```bash
mcpx sync
```

On first run, mcpx will:
1. Detect all installed platforms (check config file existence)
2. Auto-import existing MCP configs into `~/.mcpx/config.json`
3. Run health checks on each server
4. Create backups of each platform config
5. Sync to all platforms in their native format

### Manual Configuration

1. Create `~/.mcpx/config.json`:

```json
{
  "mcpx": {
    "version": "1.0"
  },
  "servers": {
    "filesystem": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/john/projects"]
    },
    "github": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

2. Sync to all platforms:

```bash
mcpx sync
```

## Configuration

### Global Config Location

`~/.mcpx/config.json` (created automatically on first run)

### Server Types

#### Stdio Servers (command-based)

```json
{
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
  }
}
```

#### HTTP Servers (URL-based)

```json
{
  "type": "http",
  "url": "https://mcp.supabase.com/mcp",
  "headers": {
    "Authorization": "Bearer ${API_TOKEN}"
  }
}
```

### Example Configuration

```json
{
  "mcpx": {
    "version": "1.0"
  },
  "servers": {
    "github": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "brave-search": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "${BRAVE_API_KEY}"
      }
    },
    "supabase": {
      "type": "http",
      "url": "https://mcp.supabase.com/mcp"
    },
    "local-tools": {
      "type": "stdio",
      "command": "uvx",
      "args": ["my-mcp-server"],
      "env": {
        "API_KEY": "${MY_API_KEY}"
      }
    }
  }
}
```

### Environment Variable Expansion

Use `${VAR_NAME}` syntax for environment variable references:

```json
{
  "env": {
    "API_KEY": "${MY_SERVICE_API_KEY}"
  }
}
```

Variables are expanded at sync time. Set actual values in your shell profile (`~/.zshrc`, `~/.bashrc`):

```bash
export MY_SERVICE_API_KEY="actual-secret-value"
```

Supported syntax:
- `${VAR_NAME}` - Expands to environment variable value
- `${VAR_NAME:-default}` - Uses default if VAR_NAME not set

## Commands

### `mcpx sync` - Sync to All Platforms

Bidirectional merge and sync to all platforms.

```bash
mcpx sync
mcpx sync --verbose
mcpx sync --skip-health
```

**Behavior:**
1. Load existing configs from all installed platforms
2. Merge into unified config (newest wins on conflicts)
3. Run health check on each MCP server
4. Skip MCPs that fail health check (with warning)
5. Create backup of each platform config
6. Write to all platforms in their native format
7. Report results

**Flags:**
- `--verbose` - Show detailed sync progress
- `--skip-health` - Skip health check (faster, less safe)

**Exit codes:**
- `0` = All platforms synced successfully
- `1` = Partial success (some platforms failed)
- `2` = Config error (invalid JSON syntax)
- `3` = Fatal error

### `mcpx init` - Initialize Project-Level MCPs

Interactive project-level MCP selection.

```bash
mcpx init
mcpx init --servers github,filesystem,zen
```

**Behavior:**
1. Display list of available MCPs from global config
2. Interactive checkbox UI to select MCPs for this project
3. Generate project configs for supported platforms
4. Warn that Gemini/Codex/Cline don't support project-level configs

**Flags:**
- `--servers github,zen,filesystem` - Non-interactive, specify servers directly

**Creates:**
- `.mcp.json` (Claude Code)
- `.roo/mcp.json` (Roo Code)
- `.kilocode/mcp.json` (Kilo Code)

### `mcpx list` - List All MCPs

Display all servers in flat list format.

```bash
mcpx list
```

**Example output:**

```
MCPs in ~/.mcpx/config.json:

  github          npx -y @modelcontextprotocol/server-github
  filesystem      npx -y @modelcontextprotocol/server-filesystem /path
  supabase        [HTTP] https://mcp.supabase.com/mcp
  zen             /path/to/zen-mcp-server

Total: 4 servers (3 stdio, 1 http)
```

### `mcpx add <name>` - Add a New MCP Server

Add a new MCP server and auto-sync to all platforms.

**Interactive mode:**
```bash
mcpx add myserver
# Prompts for: type (stdio/http), command/url, args, env vars
# Then syncs to all platforms
```

**Non-interactive mode:**
```bash
mcpx add myserver --type stdio --command npx --args "-y,my-mcp-package"
mcpx add my-api --type http --url "https://api.example.com/mcp"
```

### `mcpx remove <name>` - Remove an MCP Server

Remove an MCP server and sync removal to all platforms.

```bash
mcpx remove myserver
# Removes from config, syncs to all platforms
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
mcpx add --help
mcpx remove --help
```

## Health Checks

Before syncing, each MCP server undergoes health validation.

### Stdio Servers
- Verify `command` exists in PATH
- Verify referenced environment variables exist (warning if missing)
- Attempt to start server with 5-second timeout
- Server must respond to initialization

### HTTP Servers
- Verify URL is valid format
- Attempt HTTP GET/HEAD to URL
- Must return 2xx or MCP-specific response

### Failed Servers
- Logged with reason
- Skipped from sync (not written to platform configs)
- Retained in master config with `"disabled": true`

Use `--skip-health` to bypass health checks (faster, but may sync broken servers).

## Project-Level Configuration

For projects that need specific MCPs, use `mcpx init`:

```bash
cd /path/to/my-project
mcpx init
```

### Project Config Format (`.mcp.json`)

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
    }
  }
}
```

### Project vs Global Behavior

When a project has `.mcp.json`:
- **Project MCPs replace global MCPs** (not additive)
- Only selected MCPs are available in that project
- Provides cleaner, more predictable behavior

### Platforms Without Project Support

Gemini CLI, Codex CLI, and Cline only have global configs:
- These platforms will continue using global MCPs
- `mcpx init` displays a warning about this limitation

## Platform-Specific Details

### Claude Code

- **Global config:** `~/.claude.json`
- **Project config:** `.mcp.json` in project root
- **Format:** JSON with `mcpServers` key

### Gemini CLI

- **Global config:** `~/.gemini/settings.json`
- **Project config:** Not supported
- **Format:** JSON with `mcpServers` key
- **Preserves:** Other settings in file

### Codex CLI

- **Global config:** `~/.codex/config.toml`
- **Project config:** Not supported
- **Format:** TOML with `mcp_servers` key (snake_case)

### Cline (VS Code)

- **Global config:** `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- **Project config:** Not supported
- **Format:** JSON with `mcpServers` key
- **Adds:** `disabled: false`, `alwaysAllow: []` defaults

### Roo Code (VS Code)

- **Global config:** `~/Library/Application Support/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json`
- **Project config:** `.roo/mcp.json`
- **Format:** JSON with `mcpServers` key
- **Adds:** `disabled: false`, `alwaysAllow: []` defaults

### Kilo Code (VS Code)

- **Global config:** `~/Library/Application Support/Code/User/globalStorage/kilocode.kilo-code/settings/mcp_settings.json`
- **Project config:** `.kilocode/mcp.json`
- **Format:** JSON with `mcpServers` key
- **Adds:** `disabled: false`, `alwaysAllow: []` defaults

## Backup System

### Automatic Backups

Every sync creates automatic backups in `~/.mcpx/backups/`:

```
~/.mcpx/backups/
├── claude_20250108_143022.json
├── gemini_20250108_143022.json
├── codex_20250108_143022.toml
└── ...
```

**Format:** `<platform>_<timestamp>.<ext>`

### Retention Policy

- Keeps last **5 backups per platform**
- Older backups are automatically deleted
- Created before each sync write

## Sync Behavior

### Bidirectional Merge Strategy

1. **Collect**: Load MCPs from all installed platforms
2. **Deduplicate**: Same MCP name across platforms = potential conflict
3. **Resolve**: Newest modification timestamp wins
4. **Merge**: Union of all unique MCPs into master config
5. **Distribute**: Write master config to each platform's format

### Error Handling

- **Platform fails**: Continue syncing other platforms, report failure at end
- **Config parse error**: Exit with code 2, show line/column of error
- **No platforms found**: Warning, sync to available platforms only

## Troubleshooting

### "Command not found" Error

**Problem:** Server command doesn't exist on PATH.

**Solution:**
1. Install the required tool (e.g., `npm install -g npx`)
2. Use full path to command in config
3. Run `mcpx sync --verbose` to see health check details

### "Config file not found"

**Problem:** `~/.mcpx/config.json` doesn't exist.

**Solution:** Run `mcpx sync` - it will auto-generate the config from existing platforms.

### "Permission denied" when writing config

**Problem:** No write access to platform config directory.

**Solution:**
1. Check directory permissions: `ls -la ~/.claude.json`
2. Fix permissions: `chmod u+w ~/.claude.json`

### Health check failing

**Problem:** Server fails health check and is skipped.

**Solution:**
1. Run `mcpx sync --verbose` to see detailed error
2. Fix the server configuration or environment
3. Use `mcpx sync --skip-health` to force sync (not recommended)

### Environment variables not expanding

**Problem:** `${VAR}` not replaced with actual value.

**Solution:**
1. Ensure variable is set in shell: `echo $MY_VAR`
2. Use correct syntax: `${VAR_NAME}` (not `$VAR_NAME`)
3. Export variable: `export MY_VAR=value`

## Example Workflows

### Initial Setup

```bash
# First run - imports existing configs from all platforms
mcpx sync
# Output: Found 18 MCPs across 4 platforms. Created ~/.mcpx/config.json

# View what was imported
mcpx list
```

### Adding a New MCP

```bash
# Interactive
mcpx add weather
# Prompts for type, command/url, args, env
# Auto-syncs to all platforms

# Non-interactive
mcpx add github --type stdio --command npx --args "-y,@modelcontextprotocol/server-github"
```

### Removing an MCP

```bash
mcpx remove old-server
# Removes from config and all platforms
```

### Project Setup

```bash
cd my-project
mcpx init
# Interactive: Select MCPs for this project
# Creates .mcp.json with selected MCPs
```

### Manual Config Edit

```bash
# Edit master config
nano ~/.mcpx/config.json

# Push changes to all platforms
mcpx sync
```

## Development

### Running from Source

```bash
git clone https://github.com/yourusername/mcp-multiverse.git
cd mcp-multiverse
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

MIT License - see LICENSE file for details.

## Changelog

### v0.1.0 (2026-01-08)

- Initial release
- Support for 6 AI coding platforms (Claude, Gemini, Codex, Cline, Roo, Kilo)
- JSON configuration format with environment variable expansion
- Stdio and HTTP server support
- Bidirectional sync with newest-wins conflict resolution
- Health checks for all server types
- Backup system with 5-backup retention per platform
- Project-level MCP configuration (Claude, Roo, Kilo)
- Interactive `mcpx init` for project setup
- `mcpx add` and `mcpx remove` commands
- Comprehensive validation and error reporting
