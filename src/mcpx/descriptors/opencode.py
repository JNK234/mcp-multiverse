# ABOUTME: OpenCode descriptor — MCP in ~/.config/opencode/opencode.jsonc under `mcp` (JSONC).
# ABOUTME: type local/remote; command is a SINGLE array (binary+args); env key is `environment`.
from __future__ import annotations

from mcpx.descriptors.types import (
    FieldMap,
    MCPSpec,
    ToolDescriptor,
    command_array_from_native,
    command_array_to_native,
)
from mcpx.ir import Transport
from mcpx.update import UpdateRecipe

# OpenCode uses local/remote (NOT stdio/http). Custom transforms, not the shared helper.
_TRANSPORT = FieldMap(
    ir_field="transport",
    native_key="type",
    to_native=lambda t: "local" if t is Transport.STDIO else "remote",
    from_native=lambda v: Transport.STDIO if v == "local" else Transport.HTTP,
)

# command + args collapse into a single "command" array; reading splits it back.
_COMMAND_ARRAY = FieldMap(
    ir_field="__command_array__",
    native_key="command",
    to_native=command_array_to_native,
    from_native=command_array_from_native,
    composite=True,
)

# disabled (IR) <-> enabled (native), negated.
_ENABLED = FieldMap(
    ir_field="disabled",
    native_key="enabled",
    to_native=lambda d: not d,
    from_native=lambda e: not e,
    omit_if_empty=False,
)

OPENCODE = ToolDescriptor(
    id="opencode",
    display_name="OpenCode",
    config_paths={"mcp": "~/.config/opencode/opencode.jsonc"},
    fmt="jsonc",
    update=UpdateRecipe(command=["opencode", "upgrade"]),
    mcp=MCPSpec(
        container_key="mcp",
        supports_http=True,
        fields=(
            _TRANSPORT,
            _COMMAND_ARRAY,
            FieldMap("env", "environment"),
            FieldMap("url", "url"),
            FieldMap("headers", "headers"),
            _ENABLED,
        ),
    ),
)
