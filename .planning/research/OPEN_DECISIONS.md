# Open Decisions — before building the universal sync

## RESOLVED (user, 2026-06-22)
1. **Default-on vs opt-in categories** → **MCP + rules default-on; skills / permissions / hooks opt-in** (per-category `--category` flags).
2. **Model/provider sync** → **DO NOT SYNC model/provider at all.** Category dropped from scope. (Eliminates model-id portability risk + Cline globalState write problem.) Removes `ModelConfig`, model `LastWriterWins`, and all model mapping rules from the design.
3. **Hub scope** → **user-global first; project-scope (`.mcp.json`, `.claude/`, `AGENTS.md` per repo) is a later phase.**
4. **Next step** → **write the Phase 0 implementation plan** for approval (no code yet).

## STILL OPEN (recommended default in **bold**; will take defaults unless you say otherwise)
5. **Secrets depth.** **Reference-only: never store literals, redact on import** — OR also integrate OS keychain to resolve `{env:NAME}` at write time. (Only relevant once the env category lands, Phase 3.)
6. **Config migration.** **v1 `{mcpx,servers}` → v2 `{mcpx,categories}` auto-migration + one-time backup**; keep reading v1 indefinitely. (Decided in the Phase 0 plan.)
7. **Unverified Claude features.** **Preserve-verbatim, never-synthesize** for advanced hooks (http/mcp_tool/prompt), output-style frontmatter, settings.json env `${VAR}`. (Relevant Phase 2/4.)
8. **Conflict resolution UX.** When hub and tool-local versions of a non-server item differ: **hub is always source-of-truth** — OR interactive / last-modified-wins. (Relevant Phase 1.)
9. **OpenCode directory naming.** **Plural (`agents/`, `commands/`)** is canonical. (Relevant Phase 2.)
10. **Pull direction.** Per-category `mcpx pull` (tool→hub) in addition to push? (Later phase.)

## Confirmed bugs to fix in Phase 0 (not decisions — just do them)
- `src/mcpx/platforms/cline.py` writes `alwaysAllow` → must be `autoApprove` (Cline ignores `alwaysAllow`).
- Cline remote servers must emit `type: streamableHttp` explicitly (bug #6767).
- `src/mcpx/platforms/codex.py` drops HTTP servers + raises NotImplementedError for project config — Codex **does** support HTTP MCP and project `.codex/config.toml`. Remove stale filters.
