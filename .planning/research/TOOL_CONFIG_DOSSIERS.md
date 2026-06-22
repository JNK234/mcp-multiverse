# Tool Config Dossiers — Claude Code, OpenCode, Cline, Codex

**Date:** 2026-06-22
**Method:** Parallel per-tool research → adversarial verification against primary sources (official docs + GitHub source). Each claim below was either confirmed against a primary source or flagged. Confidence: **high** for all four tools.

> Supersedes the OpenCode/Codex shapes in `RESEARCH_MEMO.md` (issue #9), which had errors (OpenCode is **not** TOML; its MCP key is `mcp` not `mcpServers`; Codex **does** support HTTP MCP).

---

## 0. MCP shape divergence (the crux for translation)

| | Claude Code | OpenCode | Cline | Codex |
|---|---|---|---|---|
| **Config key** | `mcpServers` | `mcp` | `mcpServers` | `[mcp_servers.<name>]` (TOML) |
| **Format** | JSON | JSON / JSONC | JSON | TOML (snake_case) |
| **Type discriminator** | `type`: `stdio`/`http`/`sse`/`ws` | `type`: `local`/`remote` | `type`: `stdio`/`sse`/`streamableHttp` | auto (command⇒stdio, url⇒streamable_http) |
| **stdio command** | `command` (string) + `args` (array) | `command` (**single array** binary+args) | `command` + `args` | `command` + `args` |
| **env key name** | `env` | `environment` | `env` | `env` (TOML table) |
| **HTTP/remote** | `url` + `headers` | `url` + `headers` | `url` + `headers` | `url` + `http_headers` + `bearer_token_env_var` + `env_http_headers` |
| **Disable** | (entry removal) | `enabled: false` | `disabled: true` | `enabled: false` |
| **Auto-approve** | permissions allow rules | (permission system) | `autoApprove: []` | per-tool `approval_mode` |
| **Timeout** | `timeout` (ms) | `timeout` (default 5000ms) | `timeout` (sec, default 60) | `startup_timeout_sec` / `tool_timeout_sec` |
| **Var expansion** | `${VAR}` / `${VAR:-default}` | `{env:VAR}` / `{file:path}` | none | `env_key` = env-var **name** (no inline `${}`) |

**Translation-critical:** OpenCode merges binary+args into a single `command` array and renames `env`→`environment`. The canonical model must keep `command`/`args` split and normalize on read/write.

---

## 1. Claude Code (the sync hub / reference)

**Config files**
- `~/.claude/settings.json` (user), `.claude/settings.json` (project, committed), `.claude/settings.local.json` (project, gitignored), `managed-settings.json` (enterprise, highest precedence).
- `~/.claude.json` — app state **and** MCP servers: top-level `mcpServers` (user scope) + `projects."<path>".mcpServers` (local scope). **Not** the same file as `settings.json`.
- `.mcp.json` (project root) — project MCP servers, top-level `mcpServers`, git-committed, requires approval.
- Memory: `~/.claude/CLAUDE.md` (user), `./CLAUDE.md` or `.claude/CLAUDE.md` (project), `CLAUDE.local.md` (gitignored), `.claude/rules/*.md` (modular, support `paths:` glob frontmatter).
- Skills `~/.claude/skills/<name>/SKILL.md` & `.claude/skills/`; subagents `.claude/agents/*.md`; slash commands `.claude/commands/*.md` (**merged into skills** — both `commands/deploy.md` and `skills/deploy/SKILL.md` create `/deploy`); output-styles `~/.claude/output-styles/`.
- Auto-memory: `~/.claude/projects/<project>/memory/MEMORY.md`. Subagent persistent memory is a **separate** store: `~/.claude/agent-memory/<name>/` (corrected during verification — do not conflate the two).

**MCP** — `mcpServers` key. stdio: `type`(opt)/`command`/`args`/`env` + optional `timeout`(ms)/`alwaysLoad`. http: `type: "http"` (alias `streamable-http`) + `url`/`headers`; `sse` is **deprecated**, `ws` (WebSocket) also supported. Three scopes (local > project > user), whole-entry-wins (no field merge). `${VAR}`/`${VAR:-default}` expansion in command/args/env/url/headers only. Project-server trust via top-level `enableAllProjectMcpServers` / `enabledMcpjsonServers` / `disabledMcpjsonServers` (NOT inside `permissions`).

**Permissions** — `settings.json` `permissions { allow, ask, deny }` arrays of `Tool(specifier)` rules (e.g. `Bash(npm run test *)`, `Read(./.env)`), plus `defaultMode` (`default`/`acceptEdits`/`plan`/`bypassPermissions`) and `additionalDirectories`. Managed `permissions.deny` is unbreakable.

**Model/provider** — `model` (alias/id) + `env` block (`ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL`, `CLAUDE_CODE_USE_BEDROCK/VERTEX`) + `apiKeyHelper`. Subagent/skill `model` frontmatter. Aliases: sonnet/opus/haiku/fable/`inherit`.

**Other** — `hooks` (PreToolUse/PostToolUse/Stop/Notification; `matcher` + `hooks[].{type:command, command}`), `statusLine` (`{type:command, command, padding}`), `outputStyle`, `env`, plugins/marketplaces.

**Verification corrections**: Windows managed paths are `C:\Program Files\ClaudeCode\` (not ProgramData); `includeCoAuthoredBy` is deprecated → `attribution`; subagent `permissionMode` also accepts `auto`/`dontAsk`.

**Unverified (preserve verbatim, do not synthesize writers)**: advanced hook types (`http`/`mcp_tool`/`prompt`) and newer events; output-style `.md` frontmatter; whether `settings.json` `env` supports `${VAR}`.

---

## 2. OpenCode (sst/opencode)

**Config files** — `opencode.json` / `opencode.jsonc` (project), `~/.config/opencode/opencode.json[c]` (global, XDG-aware). `$schema`: `https://opencode.ai/config.json`. TUI in `~/.config/opencode/tui.json`. Auth in `~/.local/share/opencode/auth.json` (written by `/connect`). Rules: `AGENTS.md` (primary, walks up) + global `~/.config/opencode/AGENTS.md`, with `CLAUDE.md` as **fallback** (reads Claude's file unchanged). Agents `~/.config/opencode/agents/*.md` & `.opencode/agents/*.md` (**plural** — corrected). Commands `…/commands/*.md` (**plural** — corrected). Themes `…/themes/*.json`.

**MCP** — top-level `mcp` key. `McpLocalConfig = { type:"local"; command: string[]; environment?: Record<string,string>; enabled?: bool; timeout? }`. `McpRemoteConfig = { type:"remote"; url; headers?; enabled?; oauth?: {clientId?,clientSecret?,scope?} | false; timeout? }`. Default timeout 5000ms.

**Rules** — `AGENTS.md` + `instructions[]` array (file paths, **globs**, **remote URLs** with 5s fetch). `instructions[]` has no Claude analog (Claude uses `@import` inside CLAUDE.md) → lossy.

**Permissions** — `permission`: bare string (`allow`/`ask`/`deny`), OR map `tool→action`, OR `tool→{pattern:action}` (bash/edit), **last-match-wins**. `tools`: map `tool→bool` (hard enable/disable, valid at top level — corrected). Tool keys: read/edit/glob/grep/bash/task/skill/lsp/question/webfetch/websearch/external_directory/doom_loop.

**Model/provider** — `model: "provider/model"` + `small_model`; `provider{}` with npm AI-SDK pkg + `options.baseURL/apiKey` (`{env:VAR}`); `disabled_providers[]`; catalog from models.dev (75+). Expansion is `{env:VAR}`/`{file:path}`, **not** `${VAR}`.

**Other** — agents (`mode`: `primary`/`subagent`/`all` — corrected, three values; **no** `default_agent` field); `formatter`; `keybinds`; `share`: `manual`/`auto`/`disabled`; themes.

---

## 3. Cline (cline/cline VS Code extension, publisher `saoudrizwan.claude-dev`)

**Config files** — `…/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json` (MCP, **global only**, checks `Code` and `Code - Insiders`). Rules: `.clinerules` **file OR** `.clinerules/` **directory** of `.md`/`.txt` (NN- ordering); global `~/Documents/Cline/Rules`; auto-reads `AGENTS.md`, `~/.agents/AGENTS.md`, `.cursorrules`, `.windsurfrules` (all toggleable in UI). Workflows `.clinerules/workflows/*.md` + `~/Documents/Cline/Workflows/*.md` (invoked `/name.md`). `.clineignore` (gitignore syntax). Model/provider config + API keys live in VS Code **globalState + SecretStorage** (binary/encrypted — **not** a writable file).

**MCP** — `mcpServers` key. stdio: `command`/`args`/`env`/`cwd`/`disabled`/`autoApprove: []`/`timeout`(sec). Remote: `type`: `sse` | `streamableHttp` + `url`/`headers`. Defaults: `DEFAULT_MCP_TIMEOUT_SECONDS=60`, `MIN=1`.

> ⚠️ **BUG IN EXISTING mcpx CODE** (verified against source + the local file): `src/mcpx/platforms/cline.py` writes `"alwaysAllow": []` — Cline has **no** such field; the correct key is `"autoApprove"` (`alwaysAllow` is Roo/Kilo terminology and is silently ignored by Cline's Zod schema). **Fix in Phase 0.**

> ⚠️ **Bug #6767** (real, Oct 2025): a URL-only remote config matches Cline's SSE schema before StreamableHttp → defaults to deprecated SSE. The adapter must always emit `"type": "streamableHttp"` explicitly.

**Permissions** — per-server `autoApprove[]` + `disabled` (syncable, in the JSON file). Global `autoApprovalSettings` lives in globalState (UI/binary → low syncability).

**Model/provider** — globalState `ApiConfiguration` with mode-prefixed keys (`planModeApiProvider`/`actModeApiProvider`/`…ApiModelId`, `anthropicBaseUrl`, etc.); secrets in SecretStorage (`apiKey`, `openRouterApiKey`, …). Plan/Act dual model. **Effectively read-only for an external sync tool** — only the MCP JSON file is cleanly syncable.

> Note: `~/.cline/mcp.json` (standalone CLI path) is **unconfirmed** for the official CLI — that path comes from a third-party `@yaegaki/cline-cli`; official CLI MCP path is undocumented (issue #7249). Treat as unverified.

---

## 4. Codex CLI (openai/codex)

**Config files** — `~/.codex/config.toml` (primary; `CODEX_HOME` defaults to `~/.codex`). Project `.codex/config.toml` (walked root→cwd, closest wins — **mcpx codex.py currently raises NotImplementedError for project, out of date**). Profiles via `~/.codex/<name>.config.toml` (current) or `[profiles.<name>]` table (legacy). Rules: `~/.codex/AGENTS.md` + `AGENTS.override.md`; project `AGENTS.md` per directory (root→cwd, closest wins), capped by `project_doc_max_bytes` (default **32768**). Auth `~/.codex/auth.json`.

**MCP** — `[mcp_servers.<name>]` TOML. Transport auto-selected: `command`⇒stdio, `url`⇒streamable_http. stdio: `command`/`args`/`env`(table)/`cwd`/`startup_timeout_sec`(legacy `_ms`)/`tool_timeout_sec`/`enabled`/`required`/`enabled_tools`/`disabled_tools`/`default_tools_approval_mode`. http: `url`/`bearer_token_env_var`/`http_headers`/`env_http_headers`/OAuth. Per-tool `[mcp_servers.<name>.tools.<tool>] approval_mode`.

> ✅ **Codex DOES support HTTP/streamable MCP** — the `codex.py` comment "HTTP not supported by Codex" is **out of date**. Remove the stale filter in Phase 0.

**Permissions** — two axes: `approval_policy` (`untrusted`/`on-failure`(deprecated)/`on-request`(default)/`never`/`granular`) + `sandbox_mode` (`read-only`/`workspace-write`/`danger-full-access`). `[approval_policy.granular]` booleans: `sandbox_approval`/`rules`/`skill_approval`/`request_permissions`/`mcp_elicitations`. `[sandbox_workspace_write]` tuning. `[projects."<path>"] trust_level`. `sandbox_mode` has **no Claude analog** (OS sandbox).

**Model/provider** — `model` + `model_provider` + `[model_providers.<id>]` (`base_url`, `env_key` = env-var **name**, `wire_api = "responses"` only — `chat` removed, `http_headers`, `env_http_headers`, command-backed `[…auth]`). `model_reasoning_effort` (`none`/`minimal`/`low`/`medium`/`high`/`xhigh`), `model_reasoning_summary`, `model_verbosity`. Reserved provider ids: openai/amazon-bedrock/ollama/lmstudio. No inline `${VAR}`.

**Other** — `[profiles.<name>]`, `notify` (argv hook), `[hooks]` (lifecycle, TOML), `[shell_environment_policy]`, `[history]`, `[skills]`/`[agents]`, `web_search`.

**Verification corrections**: no `validate_reserved_model_provider_ids` fn (it's `merge_configured_model_providers`; bedrock is partially overridable); provider inline token is `experimental_bearer_token` while MCP inline is `bearer_token` (distinct fields).
