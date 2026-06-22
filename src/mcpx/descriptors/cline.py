# ABOUTME: Cline descriptor — MCP in VS Code globalStorage cline_mcp_settings.json (JSON, global).
# ABOUTME: Fixes 2 bugs: writes autoApprove (not alwaysAllow); remote type=streamableHttp (#6767).
from __future__ import annotations

from mcpx.descriptors.types import (
    FieldMap,
    MCPSpec,
    ToolDescriptor,
    vscode_globalstorage_path,
)
from mcpx.ir import Transport

# Cline transport: stdio -> "stdio"; http -> "streamableHttp" (explicit, avoids SSE-default #6767).
_TRANSPORT = FieldMap(
    ir_field="transport",
    native_key="type",
    to_native=lambda t: "stdio" if t is Transport.STDIO else "streamableHttp",
    from_native=lambda v: Transport.STDIO if v == "stdio" else Transport.HTTP,
)

CLINE = ToolDescriptor(
    id="cline",
    display_name="Cline",
    config_paths={
        "mcp": vscode_globalstorage_path("saoudrizwan.claude-dev", "cline_mcp_settings.json")
    },
    fmt="json",
    mcp=MCPSpec(
        container_key="mcpServers",
        supports_http=True,
        fields=(
            _TRANSPORT,
            FieldMap("command", "command"),
            FieldMap("args", "args"),
            FieldMap("env", "env"),
            FieldMap("url", "url"),
            FieldMap("headers", "headers"),
            # FIX: Cline's auto-approve key is `autoApprove`, NOT `alwaysAllow`.
            FieldMap("auto_approve", "autoApprove"),
        ),
        # Cline expects a `disabled` flag on each server entry.
        defaults=(("disabled", False),),
    ),
)
