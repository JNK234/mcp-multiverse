# ABOUTME: Codex CLI descriptor — MCP in ~/.codex/config.toml under [mcp_servers.<name>] (TOML).
# ABOUTME: HTTP IS supported (url/http_headers/bearer); transport inferred, no `type` key.
from __future__ import annotations

from mcpx.descriptors.types import FieldMap, MCPSpec, ToolDescriptor

CODEX = ToolDescriptor(
    id="codex",
    display_name="Codex CLI",
    config_paths={"mcp": "~/.codex/config.toml"},
    fmt="toml-flat",
    mcp=MCPSpec(
        container_key="mcp_servers",
        # Codex DOES support streamable HTTP MCP. (Old mcpx dropped HTTP — that was a bug.)
        supports_http=True,
        # No `type` discriminator: Codex infers stdio (command) vs streamable_http (url).
        # The engine infers IR.transport from url presence on read; nothing to write.
        fields=(
            FieldMap("command", "command"),
            FieldMap("args", "args"),
            FieldMap("env", "env"),
            FieldMap("url", "url"),
            FieldMap("headers", "http_headers"),
            FieldMap("bearer_token_env_var", "bearer_token_env_var"),
        ),
    ),
)
