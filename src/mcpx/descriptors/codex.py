# ABOUTME: Codex CLI descriptor — MCP in ~/.codex/config.toml under [mcp_servers.<name>] (TOML).
# ABOUTME: HTTP IS supported (url/http_headers/bearer); transport inferred, no `type` key.
from __future__ import annotations

from mcpx.descriptors.types import FieldMap, HTTPBridge, MCPSpec, ToolDescriptor
from mcpx.update import UpdateRecipe

CODEX = ToolDescriptor(
    id="codex",
    display_name="Codex CLI",
    config_paths={"mcp": "~/.codex/config.toml"},
    fmt="toml-flat",
    update=UpdateRecipe(command=["codex", "update"]),
    mcp=MCPSpec(
        container_key="mcp_servers",
        # Codex 'supports' HTTP at the config level, but its native streamable-HTTP client
        # fails the handshake with SSE servers (e.g. z.ai), so we BRIDGE HTTP via stdio
        # mcp-remote instead. supports_http stays True so HTTP servers aren't skipped.
        supports_http=True,
        # HTTP servers render as: npx -y mcp-remote <url> --header "Name: Value"
        # (verified to connect where Codex's native HTTP client throws on the
        #  `initialized` notification — a known upstream Codex bug).
        http_bridge=HTTPBridge(command="npx", base_args=("-y", "mcp-remote")),
        # stdio servers map normally; transport inferred from url presence on read.
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
