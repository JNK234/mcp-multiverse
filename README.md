# Universal MCP Sync Manager

Automatically sync and manage MCP servers across Claude Code, Gemini CLI, Cline, and Roo Code.

## Quick Start

1. **Make executable:**
```bash
chmod +x mcp-sync-manager.py
```

2. **List current servers:**
```bash
python3 mcp-sync-manager.py list
```

3. **Sync everything:**
```bash
python3 mcp-sync-manager.py sync
```

## Commands

### `list` - Show all servers
```bash
python3 mcp-sync-manager.py list
```
Shows all MCP servers configured across platforms.

### `sync` - Sync to all platforms
```bash
python3 mcp-sync-manager.py sync
```
Merges and syncs all servers to:
- Claude Code (`~/.claude/claude_desktop_config.json`)
- Gemini CLI (`~/.gemini/settings.json`)
- Cline (`~/Library/Application Support/.../cline_mcp_settings.json`)
- Roo Code (`~/Library/Application Support/.../cline_mcp_settings.json`)

### `sync --from <platform>` - Sync from specific platform
```bash
python3 mcp-sync-manager.py sync --from gemini
```
Options: `claude`, `gemini`, `cline`, `roo`

### `add` - Add new server
```bash
python3 mcp-sync-manager.py add my-server npx \
  --args "-y" "@myorg/server" \
  --env "API_KEY=my-key"
```

### `remove` - Remove server
```bash
python3 mcp-sync-manager.py remove my-server
```

## Easy Wrapper

Use the included `mcp-sync` wrapper:

```bash
./mcp-sync list    # List servers
./mcp-sync sync    # Sync all
./mcp-sync backup  # Create backups
./mcp-sync help    # Show this help
```

## How It Works

When you run `sync`:
1. Reads configs from all platforms
2. Merges all servers (deduplicates by name)
3. Backs up existing configs
4. Writes to all platforms
5. Formats correctly for each platform

## Safety

- **Backups created automatically** before every change in `~/.mcp-sync-backups/`
- **No data loss** - existing configs are preserved and backed up
- **Error handling** - invalid JSON is detected and logged
- **Logs at** `/tmp/mcp-sync-manager.log`

## Configuration Files

**Found servers across platforms:**
- Claude: `~/.claude/claude_desktop_config.json`
- Gemini: `~/.gemini/settings.json`
- Cline: VS Code extension settings
- Roo: VS Code extension settings

**Format:** All use `mcpServers` object with server definitions:
```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "package-name"],
      "env": {"API_KEY": "value"}
    }
  }
}
```

## Testing

Run tests with:
```bash
python3 -m pytest test_mcp_sync_manager.py -v
```

Tests cover:
- Data model serialization
- File I/O and formatting
- Platform-specific conversions
- Error handling
- Backup/restore
- Full sync workflow

## Troubleshooting

**"Config file not found"** - Normal for platforms you haven't used yet. Tool will create them.

**Sync fails** - Check log: `/tmp/mcp-sync-manager.log`

**Need to restore** - Backups in `~/.mcp-sync-backups/`

**Permission denied** - `chmod +x mcp-sync-manager.py`

## Project Files

- `mcp-sync-manager.py` - Main Python script
- `mcp-sync` - Bash wrapper for common commands
- `test_mcp_sync_manager.py` - Test suite
- `README.md` - This file

## Requirements

- Python 3.6+
- Access to config directories
- No external dependencies (uses only Python standard library)

---

**That's it!** List, add, remove, sync - all from one place.
