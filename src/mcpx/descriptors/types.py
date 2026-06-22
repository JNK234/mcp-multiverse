# ABOUTME: Declarative tool descriptors — the single place each tool's config truth lives.
# ABOUTME: A ToolDescriptor is pure data; engines read it to import/export, no per-tool branches.
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcpx.ir import MCPServerIR
    from mcpx.update import UpdateRecipe


@dataclass(frozen=True)
class FieldMap:
    """One traceable rule mapping an IR field to a native config key (both directions).

    ABOUTME: Simple fields use ir_field<->native_key directly (identity transforms).
    ABOUTME: Composite mappings (e.g. command+args -> single array) set composite=True and
            receive the WHOLE IR server / WHOLE native dict, returning the native value /
            a dict of IR-field updates. This is how 'no hardcoded assumptions' is kept:
            every transform is a named, inspectable rule in the descriptor.

    to_native:
        - simple: (ir_value) -> native_value
        - composite: (MCPServerIR) -> native_value
    from_native:
        - simple: (native_value) -> ir_value
        - composite: (native_dict) -> dict[str, Any]   # partial IR-field updates
    """

    ir_field: str
    native_key: str
    to_native: Callable[..., Any] | None = None
    from_native: Callable[..., Any] | None = None
    omit_if_empty: bool = True
    composite: bool = False


@dataclass(frozen=True)
class HTTPBridge:
    """Render HTTP servers as a stdio command that proxies to the URL (instead of native HTTP).

    ABOUTME: Some tools (Codex) have broken streamable-HTTP MCP clients, so HTTP servers must
    ABOUTME: run through a stdio bridge like `npx mcp-remote <url> --header <h>`. This is data:
    ABOUTME: command + a base args list; {url} is appended, and each IR header becomes
    ABOUTME: `header_flag` + "Name: Value" so the bridge forwards it. Tokens keep ${VAR} verbatim.
    """

    command: str
    base_args: tuple[str, ...]
    header_flag: str = "--header"


@dataclass(frozen=True)
class MCPSpec:
    """How one tool stores MCP servers: the container key + field mappings.

    ABOUTME: container_key is the JSON/TOML key holding the server map (e.g. mcpServers, mcp).
    ABOUTME: supports_http=False makes the engine skip+warn on http servers for this tool.
    ABOUTME: defaults are native keys force-written on every server (e.g. Cline disabled=false).
    ABOUTME: preserve_orphans is a seam for later — when True, keep unmanaged servers on write.
    ABOUTME: http_bridge (if set) makes HTTP servers render as a stdio bridge command instead.
    """

    container_key: str
    fields: tuple[FieldMap, ...]
    supports_http: bool = True
    defaults: tuple[tuple[str, Any], ...] = ()
    preserve_orphans: bool = False
    http_bridge: HTTPBridge | None = None


@dataclass(frozen=True)
class SkillsSpec:
    """How one tool stores skills — purely which frontmatter keys it can't represent.

    ABOUTME: The skill dir comes from config_paths['skills']; the SKILL.md format is shared.
    ABOUTME: drop_frontmatter_keys are removed on write (with a warning), e.g. allowed-tools.
    """

    drop_frontmatter_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolDescriptor:
    """Everything the engine needs to import/export one tool — as data, not code.

    ABOUTME: config_paths maps a logical name (e.g. 'mcp', 'skills') to a path template.
    ABOUTME: fmt selects the codec (json/jsonc/toml-flat). mcp/skills are None if unsupported.
    """

    id: str
    display_name: str
    config_paths: dict[str, str]
    fmt: str
    mcp: MCPSpec | None = None
    # How this tool self-updates (declarative recipe). None only if truly unknown.
    update: UpdateRecipe | None = None
    # How this tool stores skills (None if no skills support / not configured this cut).
    skills: SkillsSpec | None = None
    # default_kinds reserved for later (artifact porting); unused this cut.
    _reserved: dict[str, Any] = field(default_factory=dict)


# --- composite transform helpers (shared, named, traceable) ----------------

def command_array_to_native(server: MCPServerIR) -> list[str] | None:
    """IR command + args -> a single ['bin', *args] array (OpenCode's shape)."""
    if server.command is None:
        return None
    return [server.command, *server.args]


def command_array_from_native(native: dict[str, Any]) -> dict[str, Any]:
    """['bin', *args] array -> {command, args} IR-field updates (OpenCode's shape)."""
    arr = native.get("command")
    if not arr:
        return {}
    return {"command": arr[0], "args": list(arr[1:])}


def vscode_globalstorage_path(extension_id: str, filename: str) -> str:
    """Resolve a VS Code globalStorage settings file, preferring an existing Code/Insiders variant.

    ABOUTME: Shared by VS Code-hosted tools (Cline, Kilo). OS-specific user-data base.
    """
    import os
    import sys
    from pathlib import Path

    if sys.platform == "darwin":
        base = Path.home() / "Library/Application Support"
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
    else:
        base = Path.home() / ".config"

    def settings_file(variant: str) -> Path:
        return base / variant / "User/globalStorage" / extension_id / "settings" / filename

    for variant in ("Code", "Code - Insiders"):
        if settings_file(variant).exists():
            return str(settings_file(variant))
    return str(settings_file("Code"))


# Native transport-discriminator strings that mean "remote/http" across tools.
_HTTP_ALIASES = ("http", "sse", "streamable-http", "streamableHttp", "ws", "remote")


def transport_field(native_key: str = "type", *, omit_if_empty: bool = True) -> FieldMap:
    """Build a FieldMap mapping IR.transport <-> a native transport-discriminator string.

    ABOUTME: to_native emits the IR transport value; from_native classifies any known
    ABOUTME: http/remote alias as Transport.HTTP, everything else as Transport.STDIO.
    Tools with non-default native vocab (OpenCode local/remote) pass custom transforms instead.
    """
    from mcpx.ir import Transport

    return FieldMap(
        ir_field="transport",
        native_key=native_key,
        to_native=lambda t: t.value,
        from_native=lambda v: Transport.HTTP if v in _HTTP_ALIASES else Transport.STDIO,
        omit_if_empty=omit_if_empty,
    )
