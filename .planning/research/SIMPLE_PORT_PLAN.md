# mcpx — Cross-Tool Port (Skills + MCPs) via real converters

**Intent:** Port the things I actually use — **skills / commands / agents and MCP servers** — across the tools I actually have, from one place. Not a universal-settings framework. Just: take Claude's stuff, **convert it properly** into each other tool's native format, and write it there.

**Why not the big design?** The earlier `UNIVERSAL_SYNC_DESIGN.md` *would* do this, but it buried the goal under machinery you didn't ask for — a category abstraction, canonical dataclasses, a config-format migration, permissions/model/hooks/env categories, a plugin system. Over-built. This plan keeps the only two ideas that matter (Claude = source of truth; convert-and-warn) and drops the scaffolding. The big doc stays on disk as a *future option*, untouched.

**Tools detected here:** Claude Code (56 skills, ~14 agents, ~17 commands), Codex, OpenCode, Gemini, Cline, Kilo.

**Decisions (yours):**
- **Source of truth = Claude Code.** Port direction is Claude → others, but **structure the code so a `pull` (tool → Claude) can be added later without rework** (converters are written as two-way mappers from the start; only the `pull` CLI wiring is deferred).
- **Real conversion, not dump-and-skip.** Each target gets a dedicated converter that emits *that tool's native format* with frontmatter/fields translated. Warn only for genuinely unrepresentable bits — and still port everything that can be converted.
- **Global / user-level** destinations.

---

## The core: per-tool CONVERTERS (this is the whole point)

A Claude item (skill/command/agent) is `{frontmatter: dict, body: markdown, files: {path: bytes}}`. Each target converter turns that into the target's **native artifact**, mapping fields — not copying blindly.

### Claude → OpenCode
- **Skill / command** → `~/.config/opencode/command/<name>.md` with OpenCode command frontmatter: map `description`→`description`, `argument-hint`→template hint, `allowed-tools`→(note), body→template. `$ARGUMENTS`/`$1` kept (OpenCode supports them).
- **Agent (subagent)** → `~/.config/opencode/agent/<name>.md` with agent frontmatter: `description`→`description`, `model`→`model` (alias mapped, see model note), `tools`→OpenCode `tools` map, body→`prompt`. Drop `permissionMode`/`color`/`isolation` with a warning.
- **MCP** → `mcp` key, `type: local`, `command: [bin, ...args]` (join), `env`→`environment`.

### Claude → Cline
- **Skill / command** → `~/Documents/Cline/Workflows/<name>.md` (global workflow, invoked `/name.md`). Body → workflow content. Frontmatter has no Cline home → fold the useful parts (description) into a leading comment, warn on the rest.
- **Agent** → Cline has no subagent concept → **convert to a workflow** that encodes the agent's role/prompt as an explicit-instructions workflow (so it's still usable), and warn it's an approximation. *(This is the "convert appropriately" path, not skip.)*
- **MCP** → `cline_mcp_settings.json`, `autoApprove`/`disabled`/`timeout`, remote `type: streamableHttp`.

### Claude → Codex
- **Skill / command / agent** → append a `## <name>` section to `~/.codex/AGENTS.md` (Codex's instruction surface), converting the body to a self-contained instruction block; record provenance markers so re-porting replaces the same section instead of duplicating. Warn that Codex has no discrete command/skill object.
- **MCP** → `[mcp_servers.<name>]` TOML, incl. **HTTP** servers (`url`+`http_headers`).

### Claude → Gemini
- **Skill/command/agent**: Gemini has no skill/command/agent concept → fold into `GEMINI.md`/instructions if present, else **skip + warn** (the one place skip is honest).
- **MCP** → existing `mcpServers` JSON.

> **Model-alias note:** when a converter must emit a model id (OpenCode agent), translate via a tiny alias table (opus/sonnet/haiku → the target's nearest), and warn if no mapping. We do **not** sync model/provider config generally — this is only the per-agent model field on a ported agent.

---

## Code structure (small, converter-centric, reuse existing)

```
src/mcpx/porters/
  __init__.py        # run_port(kinds, targets, dry_run) -> PortReport
  model.py           # PortItem dataclass (kind, name, frontmatter, body, files, src); PortWarning
  markdown.py        # frontmatter<->body split/join (handles no-frontmatter); no heavy dep
  source_claude.py   # collect_claude_items(): walk ~/.claude/{skills,commands,agents} -> PortItem[]
  convert/
    opencode.py      # OpenCodeConverter: to_command / to_agent / mcp ; supports(kind)
    cline.py         # ClineConverter: to_workflow (skill/cmd AND agent->workflow) ; mcp
    codex.py         # CodexConverter: to_agents_md_section ; mcp (incl HTTP)
    gemini.py        # GeminiConverter: instructions-or-skip ; mcp
```
- Each converter is the **two-way mapper** (write now; a future `from_native()` enables pull). Converters only write their own files and **never clobber** unrelated config (reuse existing `read/write_json_file`, `write_toml_simple`, `create_backup`).
- MCP porting reuses the existing adapters/`sync_all` — but the **3 confirmed bugs get fixed** so MCP ports are correct.

## New CLI: `mcpx port`
```
mcpx port                       # convert+port skills+commands+agents AND MCPs, Claude -> all detected tools
mcpx port --skills              # only skills/commands/agents
mcpx port --mcp                 # only MCP servers
mcpx port --to opencode,cline   # limit targets
mcpx port --dry-run             # full plan + every warning, writes nothing
```
- `--dry-run` prints, per tool: exact files to be written, count by kind, and warnings (e.g. `Cline: agent 'gsd-planner' converted to workflow (approximation)`).
- Only targets tools whose config dir exists. Backs up any overwritten file. Grouped summary + sorted warnings.

---

## Plan of work (each step shippable, tests as we go)

1. **Fix the 3 MCP bugs** (`platforms/cline.py`: `autoApprove` + remote `type:streamableHttp`; `platforms/codex.py`: stop dropping HTTP). Update `test_cline.py`. *(small)*
2. **`porters/markdown.py` + `porters/model.py`**: frontmatter parse/emit + `PortItem`/`PortWarning`. Tests.
3. **`porters/source_claude.py`**: collect skills (incl multi-file dirs), commands, agents into `PortItem`s. Tests against a fixture `.claude` tree.
4. **`convert/opencode.py`**: command + agent + mcp converters (the richest target — real frontmatter mapping + model-alias table). Tests incl. round-trippable structure.
5. **`convert/cline.py`**: skill/command → workflow, agent → workflow-approximation, mcp. Tests.
6. **`convert/codex.py`**: AGENTS.md section converter (idempotent re-port via provenance markers) + HTTP-capable mcp. Tests.
7. **`convert/gemini.py`**: instructions-or-skip + mcp. Tests.
8. **`mcpx port` CLI** (`cli.py`): wire `run_port`, flags, detected-tool gating, backup-on-overwrite, `--dry-run`, summary/warnings. Tests.
9. **README**: `mcpx port`, the per-tool conversion table, "Claude is the source", and the model-alias note.

## OUT of scope (keeps it simple)
General permissions/model/provider/hooks/themes/env sync · config v2 "categories" migration · the `PlatformAdapter` Protocol rewrite · project-scoped porting · the live `pull` command (but converters are built pull-ready). The universal design remains a separate future doc.

## Verification before done
- `uv run pytest` green · `uv run mypy src/mcpx --strict` clean · `uv run ruff check` clean.
- Live: `mcpx port --dry-run` shows the 56 skills + agents + commands converted per tool with sensible warnings; `mcpx port --to opencode` produces real `~/.config/opencode/command/*.md` (+ `agent/*.md`) that OpenCode loads; `mcpx port --to codex` appends clean idempotent sections to `~/.codex/AGENTS.md`.
