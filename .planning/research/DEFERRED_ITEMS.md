# Deferred Items — to fix later

Open items raised during the IR-port build (2026-06-22). Not blocking the current work; revisit after the core port + legacy cleanup land.

## 1. Literal secrets fan-out on port
**Problem:** `~/.claude.json` stores some MCP secrets as plaintext literals (e.g. a real `BRAVE_API_KEY` value, not `${VAR}`). `mcpx port` faithfully copies whatever is there, so one literal secret becomes ~7 plaintext copies (manifest + 6 tool configs). We never expand `${VAR}`, but we also don't convert literals to references.

**Why convert (the use):** keeps the real value in one place (shell env); avoids leaking via committed configs/backups; one-place rotation. **Caveat:** only safe if the value is actually exported as an env var, and each tool must expand `${VAR}` (see item 3 / Step 6).

**Options to decide later:**
- (a) Detect + warn only — flag servers with literal secrets, port as-is. [leaning recommended]
- (b) Warn + opt-in `--redact` that rewrites literals → `${VAR}` in the manifest.
- (c) Do nothing.

## 2. Unset `${VAR}` warning on import/port
**Problem:** a server referencing `${FOO}` when `$FOO` isn't set in the environment will silently break after porting (empty/unexpanded value). Cheap to detect (we already scan env values).

**Decide later:** add a warning during import/port ("server X references ${FOO}, not set in your env") — or skip.

## 3. `mcpx validate` command — scope question
**Old behavior (validation.py):** command-exists checks (is `npx` on PATH?), unset-env warnings, and live MCP health checks (spawn stdio server / POST to HTTP URL, expect an `initialize` handshake response).

**Relevance:** orthogonal to porting — porting doesn't need health. Options:
- (a) Drop it entirely; delete validation.py with the rest of legacy. [leaning recommended]
- (b) Keep a lightweight `validate` = command-exists + unset-env only (retargeted to IR).
- (c) Keep full validate incl. live health checks (most work).

Note: item 2's unset-env warning overlaps with (b); if we do item 2 we get part of validate's value for free.

## Status of the build when these were deferred
- Steps 1–4 DONE: IR + manifest + codecs; declarative descriptors for all 6 tools; generic engine; CLI (`import`/`port`/`list`) written test-first. 52 tests green, mypy strict + ruff clean. Both bug fixes (Cline autoApprove, Codex HTTP) shipped.
- Step 5 (delete legacy: models.py/platforms/sync.py/old config.py + old tests) — pending.
- Step 6 (secrets verification: launch each tool, confirm `${VAR}` resolution) — pending; ties into items 1–2.
