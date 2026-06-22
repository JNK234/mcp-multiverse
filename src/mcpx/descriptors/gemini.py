# ABOUTME: Gemini CLI descriptor — MCP in ~/.gemini/settings.json under mcpServers (JSON).
# ABOUTME: Foreign keys (selectedAuthType, theme) survive: the engine only rewrites mcpServers.
from __future__ import annotations

from mcpx.descriptors.types import FieldMap, MCPSpec, ToolDescriptor, transport_field

GEMINI = ToolDescriptor(
    id="gemini",
    display_name="Gemini CLI",
    config_paths={"mcp": "~/.gemini/settings.json"},
    fmt="json",
    mcp=MCPSpec(
        container_key="mcpServers",
        supports_http=True,
        fields=(
            transport_field("type"),
            FieldMap("command", "command"),
            FieldMap("args", "args"),
            FieldMap("env", "env"),
            FieldMap("url", "url"),
            FieldMap("headers", "headers"),
        ),
    ),
)
