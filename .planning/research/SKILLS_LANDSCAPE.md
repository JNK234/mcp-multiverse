# Skills / Agents / Commands Landscape (June 2026)

Research for porting Claude Code's skills/agents/commands to other tools. Key finding: the ecosystem **converged on a shared `SKILL.md` standard** in early 2026 — several tools even read `~/.claude/skills/` directly.

## What Claude has to port FROM
- **56 skills**: `~/.claude/skills/<name>/SKILL.md` (frontmatter `name`, `description`, optional `allowed-tools`, `model`) + helper files (`gstack` has 68 files, `playwright-skill` 7, `find-and-reach` 4 — multi-file dirs are common).
- **14 agents**: `~/.claude/agents/*.md` (frontmatter `name`, `description`, `tools` comma-list, `model`, `color`).
- **16 commands**: `~/.claude/commands/*.md` (optional frontmatter; body = prompt; `$ARGUMENTS`/`$1`).

## Capability matrix (rows = concept, cols = tool)

| | Codex | OpenCode | Gemini | Cline | Kilo |
|---|---|---|---|---|---|
| **Skills** | `~/.codex/skills/<n>/SKILL.md` · close | `~/.config/opencode/skills/` (+reads `.claude/skills/`) · close | `~/.gemini/skills/` · **identical** | `.cline/skills/` (+reads `.claude/skills/`) · close | `.kilo/skills/` (+reads `.claude/skills/`) · **identical/close** |
| **Agents** | `~/.codex/agents/*.toml` · **lossy** (md→TOML, body→developer_instructions) | `~/.config/opencode/agents/*.md` · close (tools→permission) | `~/.gemini/agents/*.md` · close (drop color, tools→array) | **none** (no user agents) | `.kilo/agents/*.md` · close |
| **Commands** | `~/.codex/prompts/*.md` (deprecated) · close | `~/.config/opencode/commands/*.md` · close | `~/.gemini/commands/*.toml` · **lossy** (md→TOML, args rewrite) | Workflows `~/Documents/Cline/Workflows/*.md` · **lossy** (no frontmatter) | `.kilo/commands/*.md` · close |

## Takeaways
- **Skills = universal win.** All 5 support SKILL.md. Gemini/Kilo byte-identical. Only common loss (except Gemini): `allowed-tools` + `model` frontmatter keys.
- **Agents = hardest.** TOML for Codex, tools→permission remap (OpenCode/Kilo), tools string→array + drop color (Gemini), unportable for Cline.
- **Commands.** md→md easy (Codex/OpenCode/Kilo); Gemini (md→TOML) + Cline (plain md) are lossy transpiles.

## Version/path caveats
- Codex: dual path `~/.codex/skills` vs newer `~/.agents/skills`; prompts deprecated in favor of skills.
- Kilo: v7 `.kilo/` vs legacy `.kilocode/`/`.roomodes`.
- Gemini: possible "Antigravity CLI" rename for free tiers ~June 2026 — verify install before porting.

## DECIDED scope for first skills cut (user, 2026-06-22)
- **Port SKILLS only** (commands/agents = later milestones).
- **Copy into each tool's native skills dir** (self-contained, even for tools that auto-read `.claude/skills/`).
- **Port full body + name + desc; warn on dropped keys** (`allowed-tools`, `model`).
- Multi-file skill dirs: copy the whole directory verbatim.

## Implementation shape (fits the existing IR/descriptor design)
- New `ArtifactIR` for a skill: `name`, `body`, `frontmatter` (verbatim dict), `files: {relpath: bytes}` (multi-file), `source`.
- `import_skills(claude)` reads `~/.claude/skills/*/SKILL.md` + helper files → manifest/store.
- Each descriptor gets a `skills_dir` (e.g. Codex `~/.codex/skills`, OpenCode `~/.config/opencode/skills`, Gemini `~/.gemini/skills`, Cline `~/.cline/skills`, Kilo `~/.kilo/skills`).
- `export_skills(desc, skills)` writes `<skills_dir>/<name>/SKILL.md` + helper files; warns on frontmatter keys the tool drops.
- New codecs: `frontmatter` (PyYAML split/join) + `skill_dir` (read/write a skill directory). Add PyYAML dep.
- CLI: `mcpx port --kind skills` (or extend `mcpx port` with a kind selector).
