# MCP Sync Manager - Quick Reference

## The 4 Commands You Need

```bash
# 1. See what you have
./mcp-sync list

# 2. Sync everything (do this regularly)
./mcp-sync sync

# 3. Add a new server
python3 mcp-sync-manager.py add my-server command --args arg1 arg2 --env KEY=value

# 4. Remove a server
python3 mcp-sync-manager.py remove my-server
```

## What It Does

**Before sync:**
- Claude: 1 server
- Gemini: 14 servers
- Cline: 7 servers

**After sync:**
- All platforms: 22 servers ✨

## Platforms Supported

- ✅ Claude Code
- ✅ Gemini CLI
- ✅ Cline
- ✅ Roo Code

## Your Files

```
MCPs/
├── mcp-sync             # Wrapper script
├── mcp-sync-manager.py  # Main Python script
└── README.md            # Full documentation
```

## Common Workflows

### Setup New Machine
```bash
git clone <repo>
cd MCPs
chmod +x mcp-sync-manager.py
./mcp-sync sync
```

### Add New MCP Server
```bash
# Example: Add GitHub MCP
./mcp-sync-manager.py add github npx \
  --args "-y" "@modelcontextprotocol/server-github" \
  --env "GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxx"
```

### Sync Daily
```bash
# Add to your .zshrc/.bashrc:
alias mcp-sync='cd ~/Developer/MCPs && ./mcp-sync sync'

# Then just run:
mcp-sync
```

## Safety Features

- ✓ Automatic backups before changes
- ✓ No data loss (merges, doesn't overwrite)
- ✓ Error handling with detailed logs
- ✓ `/tmp/mcp-sync-manager.log` for debugging

## Test Results

```bash
$ ./mcp-sync diff

Platform      | Servers
--------------|--------
Claude Code   | 22
Gemini CLI    | 22
Cline         | 22

All synced! ✅
```

## Need Help?

```bash
./mcp-sync help              # Quick commands
python3 mcp-sync-manager.py --help  # Full help
```

---

**Happy coding!** 🚀
