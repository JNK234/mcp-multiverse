# Phase 0 — Foundation Refactor (behavior-preserving) + Confirmed Bug Fixes

**Status:** PROPOSED — awaiting approval. No code written yet.
**Goal:** Introduce the settings-**category** abstraction with `mcp_servers` as the *only* category, changing **zero observable sync behavior** for the existing 6 platforms, plus fix the 3 confirmed correctness bugs. This de-risks every later phase. Existing test suite stays green (with two intentional, documented test updates for the Cline bug fix).

**Scope decisions applied:** model/provider category is **out of scope entirely** (per user). Hub stays **user-global**. After Phase 0, MCP + rules will be the default-on categories (rules arrive Phase 1).

---

## Guiding constraints

- **Behavior-preserving:** `mcpx sync`, `add`, `remove`, `list`, `init`, `validate` produce identical output and identical files (byte-for-byte where they did before), **except** the 3 bug fixes below, which are *corrections* of wrong behavior.
- **Smallest reasonable change.** Reuse `merge_servers`, `create_backup`, `expand_env_vars`, `read/write_json_file`, `write_toml_simple`, the `ALL_PLATFORMS` registry.
- **No model/provider, no rules, no skills yet** — only the structural seam + bug fixes.
- Every file starts with the two `ABOUTME:` comment lines per repo convention.
- `mypy --strict` and `ruff` stay clean.

---

## Work items

### A. The category seam (`models.py`)
Add alongside the existing `MCPServer`/`Config`/`PlatformAdapter` (do **not** delete them yet):

1. `CategoryHandler` Protocol (generic over the item type) with `category: str`, `read() -> dict[str, T]`, `write(items) -> None`, `supports_project() -> bool`, `write_project(items, project_dir) -> None`.
2. Extend `PlatformAdapter` Protocol with two **new** methods: `supported_categories() -> set[str]` and `handler(category: str) -> CategoryHandler | None`. Keep `name` and `config_path` exactly as-is.
3. **Back-compat:** keep `load()`/`save()`/`save_project()` on the Protocol for now (the MCP handler delegates to them) so nothing else breaks mid-refactor. They get removed in a later phase when no caller remains.
4. Widen `MCPServer.type` to `Literal["stdio","http","sse","ws"]` and add optional fields with safe defaults so existing construction is unaffected: `cwd: str | None = None`, `timeout: float | None = None`, `enabled: bool = True`, `auto_approve: list[str] = []`, `extras: dict[str, Any] = {}`. **All default to today's values** → existing tests that build `MCPServer(name=..., type="stdio", command=...)` keep passing unchanged.

### B. `BasePlatformAdapter` + per-tool MCP handlers (`platforms/base.py`, `platforms/<tool>.py`)
1. Add `BasePlatformAdapter` in `base.py`: stores `_handlers: dict[str, CategoryHandler]`; implements `supported_categories()` = `set(self._handlers)`, `handler(c)` = `self._handlers.get(c)`. Provides `name`/`config_path` as abstract/overridable.
2. For each existing adapter (Claude, Gemini, Codex, Cline, Roo, Kilo), wrap its current `load`/`save`/`save_project` into a small `<Tool>MCPHandler(CategoryHandler)` registered under `"mcp_servers"`. The handler's `read`/`write` call the adapter's existing methods (thin delegation — no logic moves yet, minimizing diff and risk). Each adapter registers `{"mcp_servers": handler}`.
3. Roo/Kilo/Claude handlers report `supports_project() = True`; Gemini/Codex/Cline report `False` (replacing the call-time `NotImplementedError` with an up-front capability answer — the engine checks this instead of catching the exception).

### C. Category registry + merge strategy (`categories/`)
1. New `src/mcpx/categories/__init__.py`: `MERGE_STRATEGIES: dict[str, MergeStrategy]` and `VALIDATORS: dict[str, Callable]`.
2. New `src/mcpx/categories/strategies.py`: `MergeStrategy` Protocol `merge(managed, existing, adapter) -> tuple[dict, list[SyncWarning]]`. Implement `NameKeyedUnion` by **moving the body of `merge_servers` into it verbatim** (managed wins, orphans preserved) and have the old `merge_servers` delegate to it (keep the function as a thin shim so `sync.py` and any tests still import it).
3. Register `mcp_servers -> NameKeyedUnion` and `mcp_servers -> validate_server`.

### D. Generalized sync engine (`sync.py`)
1. Generalize `sync_all(config)` → `sync_all(config, categories=None, dry_run=False)`. When `categories is None`, default to the **default-on set** (Phase 0: just `{"mcp_servers"}`).
2. New core loop: for each category × `get_adapters_for(category)`: skip if `config_path is None`; if `handler(category) is None` → record a capability-skip warning; else backup → `handler.read()` → `strategy.merge(...)` → (unless `dry_run`) `handler.write(merged)`. **This is exactly today's MCP path** with `category="mcp_servers"`, so server output is identical.
3. Keep the existing validation gate (validate all servers first, fail-fast) — now driven by `VALIDATORS["mcp_servers"]`.
4. `first_run_init()` unchanged in behavior (still imports MCP servers), but writes the v2 config shape (see E).

### E. Config schema + migration (`config.py`)
1. New canonical shape: `{"mcpx": {"version": "2.0"}, "categories": {"mcp_servers": {"scope": "user", "items": {<name>: <serverdef>}}}}`.
2. **Auto-migration reader:** `load_config` detects v1 (`{"mcpx": {"version":"1.0"}, "servers": {...}}`) and transparently maps `servers` → `categories.mcp_servers.items`. **Reads v1 indefinitely.** On the first `save` after a v1 read, write a one-time backup of the old `config.json` to `~/.mcpx/backups/` before writing v2.
3. `save_config` writes v2. `add_server_to_config`/`remove_server_from_config` operate on the `mcp_servers` category but keep their existing signatures (they still take/return `MCPServer`).
4. `Config` dataclass gains `categories`; add a `servers` **property shim** returning `categories["mcp_servers"].items` so existing code/tests using `config.servers` keep working.

### F. Warnings + report (`warnings.py`, `sync.py`)
1. New `src/mcpx/warnings.py`: `SyncWarning(category, adapter, item, lossiness, message, preserved_as)` frozen dataclass + a `lossiness` Literal.
2. Extend `SyncReport` with `warnings: list[SyncWarning] = []` and an `add_warning()`; keep all existing fields/methods. CLI prints a grouped summary line; `--verbose` lists each warning.
3. Add `--dry-run` flag to `mcpx sync` (computes merges + warnings, skips writes/backups).

### G. The 3 confirmed bug fixes
1. **Cline `alwaysAllow` → `autoApprove`** (`platforms/cline.py:96-103`): write `"autoApprove": []` instead of `"alwaysAllow": []`. Keep `"disabled": False`. **Update `tests/test_platforms/test_cline.py`** assertions accordingly (this is the one intentional test change; document why in the commit).
2. **Cline remote `type: streamableHttp`** (bug #6767): when writing an http server to Cline, emit `"type": "streamableHttp"` explicitly (never URL-only). Add a test for a remote server.
3. **Codex HTTP + project support** (`platforms/codex.py`): remove the `stdio`-only filter in `save` so http servers are written as `[mcp_servers.<name>]` with `url` + `http_headers`; remove the `NotImplementedError` in `save_project` and implement project `.codex/config.toml` writing (mirrors global). Add tests. *(If you'd rather keep Codex project-config out of Phase 0 to stay minimal, we can defer just the `save_project` part and only fix the HTTP drop — flag your preference.)*

### H. Tests
- All existing tests pass unchanged **except** the documented Cline assertion update.
- New tests: v1→v2 config migration (round-trip + one-time backup), `--dry-run` (no files written, warnings populated), capability-skip warning for unsupported project category, `NameKeyedUnion` parity with old `merge_servers`, Cline `autoApprove` + remote `streamableHttp`, Codex http write + project write.
- **New adapter conformance harness:** `read(write(x)) == x` round-trip for `mcp_servers` on every adapter (catches future shape regressions).

---

## Atomic commit sequence (each commit green)

1. `refactor: widen MCPServer with optional fields (defaults preserve behavior)`
2. `feat: add CategoryHandler + supported_categories to PlatformAdapter protocol`
3. `refactor: add BasePlatformAdapter and wrap each adapter's MCP load/save into a handler`
4. `refactor: extract merge_servers into NameKeyedUnion strategy + category registry`
5. `feat: add SyncWarning + SyncReport.warnings + --dry-run`
6. `refactor: generalize sync_all to category×adapter loop (mcp_servers only)`
7. `feat: v2 config schema {mcpx,categories} with v1 auto-migration + one-time backup`
8. `fix: Cline writes autoApprove not alwaysAllow (+ update tests)`
9. `fix: Cline emits type:streamableHttp for remote servers (#6767)`
10. `fix: Codex supports HTTP MCP servers and project config`
11. `test: adapter round-trip conformance harness for mcp_servers`

---

## Out of scope for Phase 0 (later phases)
Rules/memory sync (Phase 1) · skills/subagents/commands (Phase 2) · permissions + env/redaction (Phase 3) · hooks + plugin entry-points + `mcpx diff` (Phase 4) · model/provider (**cut entirely**) · project-scope hub model beyond per-tool `write_project` (later).

## Verification before "done"
- `uv run pytest` fully green.
- `uv run mypy src/mcpx --strict` clean.
- `uv run ruff check src tests` clean.
- Manual diff: run `mcpx sync` against a fixture home; confirm Claude/Gemini/Roo/Kilo output is byte-identical to pre-refactor, and Cline/Codex output reflects only the intended bug fixes.
