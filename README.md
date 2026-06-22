# mcpx

**Port MCP servers across your AI coding tools from one source of truth.**

Define your MCP servers once (in Claude Code), and `mcpx` converts and writes them into every other tool's native config format — Codex, OpenCode, Cline, Kilo, Gemini — handling each tool's quirks for you.

```
mcpx import          # pull MCP servers from Claude Code into ~/.mcpx/manifest.json
mcpx port            # write them to every installed tool, in that tool's own format
```

---

## Why

Every AI coding tool stores MCP servers differently:

- **Claude Code** — `mcpServers` in `~/.claude.json`, `type`/`command`/`args`/`env`
- **OpenCode** — `mcp` in `opencode.jsonc`, `type: local/remote`, `command` is a **single array**, env key is `environment`
- **Codex** — `[mcp_servers.<name>]` TOML, transport auto-detected, HTTP via `url`/`http_headers`
- **Cline** — `mcpServers` JSON, `autoApprove`, remote needs `type: streamableHttp`
- **Kilo** — `mcpServers` JSON, `alwaysAllow`, VS Code globalStorage
- **Gemini** — `mcpServers` JSON in `~/.gemini/settings.json`

Keeping these in sync by hand is tedious and error-prone. `mcpx` maps them all to one canonical representation and writes each tool's correct shape — **without ever clobbering your other settings** (`$schema`, themes, auth, etc. are preserved).

## Install

```bash
uv pip install -e .      # from source
# or
pip install -e .
```

Requires Python 3.12+.

## Commands

### `mcpx import` — pull servers into the manifest

```bash
mcpx import                 # from Claude Code (default source)
mcpx import --from claude
```

Reads the source tool's MCP config and writes the canonical manifest at `~/.mcpx/manifest.json`. This is the editable source of truth — you can hand-edit it if you like.

### `mcpx list` — show what's in the manifest

```bash
mcpx list
```

```
MCP servers in ~/.mcpx/manifest.json:

  github                   [stdio] npx
  filesystem               [stdio] npx
  web-search-prime         [http] https://api.z.ai/api/mcp/web_search_prime/mcp

Total: 3 server(s)
```

### `mcpx update` — update all your CLI tools

```bash
mcpx update
```

Updates every installed CLI tool in one shot, each via its own updater:

```
✓ Claude Code: updated        # claude update
✓ Gemini CLI: updated         # npm install -g @google/gemini-cli@latest
✓ Codex CLI: updated          # codex update
✓ OpenCode: updated           # opencode upgrade
· Cline: Update via VS Code Extensions panel
· Kilo Code: Update via VS Code Extensions panel
Update complete: 4 updated, 0 failed.
```

Each tool's update command is a declarative recipe on its descriptor (traceable, no hardcoded branches). Tools that aren't installed are skipped; VS Code extensions (Cline, Kilo) print guidance since they can't be updated from a shell.

### `mcpx port` — write servers to your tools

```bash
mcpx port                       # to every installed tool (auto-detected)
mcpx port --to opencode         # to one tool
mcpx port --to opencode,codex   # to several
mcpx port --dry-run             # preview exactly what would be written — writes nothing
```

- **Auto-detects installed tools** (those whose config directory exists) and excludes the source.
- **Backs up** any file it overwrites to `~/.mcpx/backups/` (keeps the last 5 per tool).
- **Preserves foreign settings** — only the MCP block is rewritten; `$schema`, themes, auth, and everything else stay put.
- **Warns, never silently drops** — e.g. an HTTP server going to a tool without HTTP support is skipped with a message.

Always safe to run `--dry-run` first.

## Typical workflow

```bash
# 1. You added a new MCP server in Claude Code. Pull it in:
mcpx import

# 2. See what would change everywhere:
mcpx port --dry-run

# 3. Apply it:
mcpx port

# 4. Confirm a tool actually loaded it (OpenCode example):
opencode mcp list
```

## How it works

```
Claude Code ──import──▶  Canonical IR  ──port──▶  Codex / OpenCode / Cline / Kilo / Gemini
   (source)            (~/.mcpx/manifest.json)        (each tool's native format)
```

- **Canonical IR** (`ir.py`) — one tool-agnostic `MCPServerIR` (the superset of every tool's fields). An `extra` field preserves any native field that has no canonical home, so nothing is lost.
- **Declarative descriptors** (`descriptors/*.py`) — each tool is described by **pure data**: where its config lives, its format, and a list of `FieldMap`s. To see how `command + args` becomes OpenCode's single array, you read **one line** in `descriptors/opencode.py`. There are **no `if tool == "x"` branches** in the engine.
- **One generic engine** (`engine/mapping.py`) — applies the descriptor's `FieldMap`s in both directions. Because import and export are symmetric, reverse-sync (tool → Claude) and tool ↔ tool are natural future extensions.
- **Format codecs** (`codecs/`) — read/write JSON, JSONC (comment-tolerant, preserves `$schema`), and TOML, preserving everything they don't manage.

### Per-tool quirks handled for you

- **Codex + HTTP servers** — Codex's native streamable-HTTP MCP client can't complete the handshake with SSE-style servers (a known upstream bug). So mcpx ports HTTP servers to Codex as a **stdio bridge** — `npx -y mcp-remote <url> --header "Authorization: Bearer …"` — which connects reliably (verified: zero handshake errors). stdio servers are written natively. This requires Node/`npx` (the first run downloads `mcp-remote`). Other tools (OpenCode, Cline) get native HTTP, which they handle fine.

### Secrets

`mcpx` writes `${VAR}` references **verbatim** — it never expands them into literal values, so it won't scatter plaintext secrets across config files. (If your *source* already stores a literal secret, mcpx carries it as-is; it doesn't invent references. See `.planning/research/DEFERRED_ITEMS.md`.)

## Adding a new tool

Adding support for another tool is a one-file, data-only change — no engine edits:

1. Create `src/mcpx/descriptors/<tool>.py` with a `ToolDescriptor`: its `config_paths`, `fmt` (`json`/`jsonc`/`toml-flat`), and an `MCPSpec` whose `fields` are `FieldMap`s mapping each IR field to that tool's native key (with `to_native`/`from_native` transforms for any quirks).
2. Add it to `REGISTRY` in `src/mcpx/descriptors/__init__.py`.

That's it — `import`, `port`, `list`, and auto-detection pick it up.

## Development

```bash
uv run pytest                      # tests
uv run mypy src/mcpx --strict      # type check
uv run ruff check src tests        # lint
```

## Status & scope

- ✅ **MCP servers** — port across all six tools. Verified end-to-end against OpenCode (all servers connect, including HTTP).
- 🔜 **Skills / commands / agents** — designed, not yet built. The IR/descriptor architecture has clean seams for it. See `.planning/research/`.
- See `.planning/research/DEFERRED_ITEMS.md` for known follow-ups (literal-secret detection, unset-`${VAR}` warnings, optional `validate`).

## License

MIT
