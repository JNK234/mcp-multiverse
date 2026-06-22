# Universal Settings Sync — Design

**Date:** 2026-06-22
**Goal:** Evolve mcpx from "MCP-server sync" into a **universal coding-agent settings sync manager** with **Claude Code as the canonical hub**, syncing MCP servers + rules/instructions + skills/subagents/commands + permissions + model/provider + hooks + env across Claude Code, OpenCode, Cline, Codex — and **any future tool** via a clean adapter contract.

**Decisions baked in (from user):** sync everything syncable · **best-effort map + warn** (translate what maps, preserve + warn on the rest, never silently drop) · extensible (research these 4 now, plug in any tool later) · build **on** existing mcpx (frozen dataclasses, `PlatformAdapter`, `sync_all`, backups, `${VAR}` expansion) — evolve, don't rewrite.

---

## The one structural blocker

mcpx's `PlatformAdapter` Protocol is **type-locked** to `dict[str, MCPServer]` around a single hardcoded key (`mcpServers`/`mcp_servers`). Everything else is reusable: the registry, orphan-preserving `merge_servers`, backups, validation gate, `${VAR}` expansion. The fix is to introduce a **settings "category"** abstraction so skills/rules/permissions/model/hooks flow through the same pipeline.

---

## Capability matrix (syncability per category)

| Category | Claude (hub) | OpenCode | Cline | Codex | Syncability |
|---|---|---|---|---|---|
| **MCP servers** | `mcpServers` | `mcp` local/remote | `mcpServers` | `[mcp_servers]` TOML | **full** (shapes diverge, normalize) |
| **Rules / instructions / memory** | CLAUDE.md + `.claude/rules` | AGENTS.md + `instructions[]` | `.clinerules` file/dir | AGENTS.md per-dir | **lossy** (path-scope/imports/globs don't round-trip) |
| **Skills / subagents / commands** | SKILL.md bundles + agents + commands | agents + commands (no bundle) | workflows only | `[skills]`/`[agents]` | **tool-specific** (Claude richest → one-way export + warn) |
| **Tool & permission policy** | `permissions{allow,ask,deny}` | `permission` map, last-match | per-server `autoApprove` | `approval_policy`+`sandbox_mode` | **lossy** (semantics differ; warn loudly) |
| **Model & provider** | `model` + env | `provider/model` | globalState (binary) | `model`+`[model_providers]` | **tool-specific** (ids non-portable; Cline unreliable) |
| **Slash / custom commands** | `.claude/commands/*.md` | `.opencode/commands` | `.clinerules/workflows` | skills subsystem | **lossy** (body maps, frontmatter doesn't) |
| **Hooks** | `settings.json hooks` | — | — | `[hooks]` + `notify` | **tool-specific** (only Claude+Codex; narrow map) |
| **Formatters/lint** | (via hooks) | `formatter{}` | — | — | **none** (only OpenCode; preserve foreign key) |
| **Themes / UI / statusline** | `statusLine`, output-styles | tui.json | `cline.*` | `[tui]` | **tool-specific** (cosmetic; preserve, don't sync) |
| **Environment & secrets** | `env` block | `{env:VAR}` | SecretStorage | `env_key`/`auth.json` | **lossy** (refs only, redact on import) |

---

## Canonical model (the hub: `~/.mcpx/`)

Two storage mediums:
- **`~/.mcpx/config.json`** — structured/keyed categories (servers, permissions, model, hooks, env, command-index).
- **`~/.mcpx/store/<category>/`** — file tree for markdown-bodied categories (rules, skills, subagents, commands, output-styles) so **bodies + frontmatter survive byte-exact**.

```python
@dataclass
class Config:
    version: str
    categories: dict[str, "CategorySet"]   # replaces {version, servers}

# CategorySet = { scope: "user"|"project", items: dict[str, CanonicalItem] }
```

Every canonical dataclass is **frozen** (matching existing `MCPServer` style) and carries `extras: dict[str, Any]` to **preserve unmapped foreign fields losslessly**.

- **`MCPServer`** (extend existing): widen `type` → `stdio`/`http`/`sse`/`ws`; keep `command`+`args` **split**; add `cwd`, `timeout`, `enabled`, `auto_approve`, `extras`. `env` values may be `{env:NAME}` refs, not literals.
- **`Rule`**: `name`, `body` (verbatim md), `frontmatter`, `kind` (memory/rule), `scope`, `source_format`.
- **`MarkdownBundle`** base → `Skill` / `Subagent` / `Command`: `name`, `body`, `frontmatter`, `files: dict[str,bytes]` (multi-file skill dirs), `scope`.
- **`PermissionRule`** (`tool`, `specifier`, `effect`) + **`PermissionPolicy`** (`rules`, `default_mode`, `additional_directories`, `extras`).
- **`ModelConfig`**: `default_model`, `small_model`, `base_url`, `provider`, `params`, `extras`.
- **`Hook`**: `event`, `matcher`, `hook_type`, `command`, `raw` (preserve advanced/unverified hook types verbatim).
- **`EnvVar`**: `name`, `ref` (`{env:NAME}`/`{file:path}` — never a literal secret), `value` (non-secret only), `is_secret`.

**Expansion semantics change per category:** servers/commands keep `${VAR}` expand-at-use, but `env`/secrets store **references** and run a **redaction gate on import** (departing from today's expand-to-literal at load).

---

## Architecture (evolves the Protocol; reuses everything else)

```python
class CategoryHandler(Protocol[T]):
    category: str
    def read(self) -> dict[str, T]: ...                  # native → canonical
    def write(self, items: dict[str, T]) -> None: ...     # canonical → native, preserve foreign keys
    def write_project(self, items, project_dir): ...      # optional
    def supports_project(self) -> bool: ...

@runtime_checkable
class PlatformAdapter(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def config_path(self) -> Path | None: ...            # unchanged existence probe
    def supported_categories(self) -> set[str]: ...       # NEW capability declaration
    def handler(self, category: str) -> CategoryHandler | None: ...
```

- `BasePlatformAdapter` holds `_handlers: dict[str, CategoryHandler]`; `supported_categories()` = its keys. Unsupported category → `handler()` returns `None` → engine records a **capability skip** (replaces today's call-time `NotImplementedError`).
- Existing `ClaudeAdapter.load/save` becomes `ClaudeMCPHandler` under `mcp_servers`; new handlers add rules/skills/permissions/model/hooks.
- **Registry unchanged**: `ALL_PLATFORMS` + `get_all_platforms()` stay; add `get_adapters_for(category)`.

**Sync engine** (`sync_all` generalized): iterate `categories × adapters`; per category pick a `MergeStrategy`; backup → `read()` existing → `strategy.merge(managed, existing, adapter)` → `write()` (unless `--dry-run`).

**Merge strategies**: `NameKeyedUnion` (servers/skills/commands — generalizes today's `merge_servers`, orphans preserved) · `MarkdownContentMerge` (rules) · `RuleSetUnion` (permissions, deny-precedence) · `LastWriterWins` (model singleton) · `PreserveOnly` (formatters/themes — never overwrite).

**File layout** under `src/mcpx/`: `categories/` (registry, strategies), `warnings.py` (`SyncWarning`), `utils/redact.py` + `utils/frontmatter.py` (new), `platforms/<tool>/` packages with one handler file per category. Retained: `MCPServer`, `merge_servers`→`NameKeyedUnion`, `create_backup`, `expand_env_vars`, `read/write_json_file`, `toml_writer`, the registry.

---

## "Best-effort map + warn" as a first-class mechanism

```python
@dataclass(frozen=True)
class SyncWarning:
    category: str; adapter: str; item: str | None
    lossiness: Literal["lossless","lossy","unmappable"]
    message: str
    preserved_as: str | None = None   # extras key / foreign key / store path
```

1. **Translate-or-preserve, never silently drop.** Every handler returns `(items, [SyncWarning])`. Unmappable fields go to `extras`/`raw`/`files` **and** emit a warning naming the field + where it's kept.
2. **Foreign-key preservation** generalizes today's `save()` (read existing, replace only the managed section) into the universal contract — themes, statusLine, formatters, provider auth all survive.
3. **Capability negotiation up front** (supported_categories) → one skip-warning per adapter, no runtime errors.
4. **Warning surfaces**: grouped CLI summary (`N synced, M warnings (K lossy, L skipped)`), `--verbose` per-item, `SyncReport.warnings`, `--json` for CI.
5. **`--dry-run`**: full merge + translation, no writes/backups — preview lossy maps. `mcpx diff` later reuses it.
6. **Redaction gate** (`utils/redact.py`): secret-pattern values (high-entropy, `sk-`/`ghp-`/`Bearer`, `*TOKEN`/`*KEY`/`*SECRET`) → reference + `is_secret=True` + warning; literal never persisted to `~/.mcpx`.
7. **Validation**: `lossy` proceeds; `unmappable`+required → skip-that-item-only, never abort the run.
8. **Deterministic** sorted warnings for stable CI output.

---

## Extensibility — adding any future tool

One file under `src/mcpx/platforms/<tool>/` that: subclasses `BasePlatformAdapter`; declares `supported_categories()` by registering only the handlers it implements; implements each `CategoryHandler` (`read`/`write`/optional `write_project`, returning `(items, warnings)`); appends to `ALL_PLATFORMS`. Zero other changes. New **categories** are equally pluggable (dataclass + strategy + ≥1 handler). **Phase 4 plugin mechanism**: Python entry points (`mcpx.adapters` group) for out-of-tree pip-installable adapters; `mcpx adapters list` prints the live capability matrix; a shared conformance harness enforces `read(write(x)) == x` for declared-lossless categories.

---

## Phased roadmap (each phase leaves mcpx fully working)

- **Phase 0 — Foundation refactor (behavior-preserving):** add category abstraction with `mcp_servers` as the *only* category; wrap existing adapters into `<Tool>MCPHandler`; generalize `sync_all`; `merge_servers`→`NameKeyedUnion`; `Config`→`{version, categories}` with **v1→v2 auto-migration**; add `SyncWarning`, `SyncReport.warnings`, `--dry-run`; **fix Cline `alwaysAllow`→`autoApprove`**; **remove stale Codex "no http" filter**; round-trip adapter test harness. *Existing tests stay green.*
- **Phase 1 — Rules / instructions / memory:** `Rule` + `utils/frontmatter.py`; Claude/OpenCode/Cline/Codex rules handlers; `MarkdownContentMerge`; warn on path-scoped/import features; import existing memory files on first run.
- **Phase 2 — Skills / subagents / commands:** `MarkdownBundle` family + multi-file store; Claude skills/agents/commands handlers; OpenCode agents/commands; Cline workflows; one-way export + warn where target lacks the concept.
- **Phase 3 — Permissions + model/provider:** `PermissionPolicy`/`PermissionRule` + `RuleSetUnion` (Claude arrays ↔ OpenCode action-map; Codex approval/sandbox, sandbox→extras); `ModelConfig` + `LastWriterWins` (intent + base_url; ids non-portable; Cline read-only/skip); `utils/redact.py` + env category (refs only).
- **Phase 4 — Hooks, env polish, output-styles + plugin extensibility:** Claude↔Codex command-hook map (advanced types verbatim in `raw`); output-styles within-Claude; formatters/themes/statusline as `PreserveOnly`; entry-point plugin discovery; `mcpx adapters list`; `mcpx diff`; `--json`; adapter-authoring docs.

---

## Key risks

- **Model-id non-portability** (opus vs gpt-5.x vs anthropic/claude-… vs gemini): never write a foreign model id verbatim; sync intent + warn; consider a curated alias map.
- **Secret leakage**: today's expand-to-literal would write real tokens into `~/.mcpx`. The redaction gate is load-bearing — must land **with** the env category.
- **Cline binary stores** (globalState/SecretStorage): declare low/none syncability, skip — don't attempt brittle binary writes.
- **Permission-semantics drift**: a mechanical map can silently weaken security (deny→ask). Treat as lossy, warn loudly, prefer stricter interpretation, gate behind opt-in.
- **Cline SSE bug #6767**: always emit `type:streamableHttp` explicitly.
- **Unverified Claude schemas** (advanced hooks, output-style frontmatter, settings.json env `${VAR}`): preserve verbatim, never synthesize.
- **Migration risk**: v1→v2 config must auto-migrate with a one-time backup and a tested back-compat reader.
