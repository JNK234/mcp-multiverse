# ABOUTME: The ONLY place IR<->native field mapping happens — driven by descriptor FieldMaps.
# ABOUTME: render_native_from_ir (export) and apply_field_maps_to_ir (import) iterate the fields.
from __future__ import annotations

from typing import Any

from mcpx.descriptors.types import MCPSpec
from mcpx.ir import MCPServerIR, Transport


def _is_empty(value: Any) -> bool:
    return value is None or value == [] or value == {} or value == ""


def _render_http_bridge(spec: MCPSpec, server: MCPServerIR) -> dict[str, Any]:
    """Render an HTTP server as a stdio bridge command (e.g. npx mcp-remote <url> --header ...).

    ABOUTME: For tools whose native HTTP MCP client is broken. Headers become `--header
    ABOUTME: "Name: Value"` args; values keep ${VAR} references verbatim. Returns a stdio dict.
    """
    bridge = spec.http_bridge
    assert bridge is not None
    args = [*bridge.base_args]
    if server.url:
        args.append(server.url)
    for name, value in server.headers.items():
        args.extend([bridge.header_flag, f"{name}: {value}"])
    return {"command": bridge.command, "args": args}


def render_native_from_ir(spec: MCPSpec, tool_id: str, server: MCPServerIR) -> dict[str, Any]:
    """Render one IR server into this tool's native server dict via the descriptor's FieldMaps.

    ABOUTME: HTTP servers route through http_bridge if the spec defines one (broken-HTTP tools).
    ABOUTME: Composite maps receive the whole server; simple maps receive one IR attribute.
    ABOUTME: Applies omit_if_empty, then forced defaults, then merges back extra[tool_id].
    """
    if server.transport is Transport.HTTP and spec.http_bridge is not None:
        return _render_http_bridge(spec, server)

    native: dict[str, Any] = {}

    for fm in spec.fields:
        if fm.composite:
            value = fm.to_native(server) if fm.to_native else None
        else:
            ir_value = getattr(server, fm.ir_field)
            value = fm.to_native(ir_value) if fm.to_native else ir_value

        if fm.omit_if_empty and _is_empty(value):
            continue
        native[fm.native_key] = value

    # Forced defaults (e.g. Cline disabled=false) unless a field map already set them.
    for key, default_value in spec.defaults:
        native.setdefault(key, default_value)

    # Round-trip native-only fields this tool produced on a prior import.
    for key, value in server.extra.get(tool_id, {}).items():
        native.setdefault(key, value)

    return native


def apply_field_maps_to_ir(
    spec: MCPSpec, tool_id: str, name: str, native: dict[str, Any]
) -> MCPServerIR:
    """Parse one tool's native server dict back into an MCPServerIR via the descriptor.

    ABOUTME: Inverse of render_native_from_ir. Unmapped native keys land in extra[tool_id]
    ABOUTME: so a later export to the same tool restores them losslessly.
    """
    updates: dict[str, Any] = {}
    consumed_native_keys: set[str] = set()

    for fm in spec.fields:
        if fm.native_key not in native:
            continue
        consumed_native_keys.add(fm.native_key)
        native_value = native[fm.native_key]
        if fm.composite:
            updates.update(fm.from_native(native) if fm.from_native else {})
        else:
            ir_value = fm.from_native(native_value) if fm.from_native else native_value
            updates[fm.ir_field] = ir_value

    # Native keys nothing mapped (and not forced defaults) are preserved in extra[tool_id].
    default_keys = {k for k, _ in spec.defaults}
    extra_native = {
        k: v
        for k, v in native.items()
        if k not in consumed_native_keys and k not in default_keys
    }

    transport = updates.pop("transport", None)
    if transport is None:
        transport = Transport.HTTP if updates.get("url") else Transport.STDIO

    server = MCPServerIR(name=name, transport=transport)
    for key, value in updates.items():
        setattr(server, key, value)
    if extra_native:
        server.extra = {tool_id: extra_native}
    return server
