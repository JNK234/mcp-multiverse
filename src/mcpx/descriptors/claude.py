# ABOUTME: Claude Code descriptor — the SOURCE OF TRUTH. MCP in ~/.claude.json under mcpServers.
# ABOUTME: stdio = type/command/args/env; http = type/url/headers. ${VAR} kept verbatim.
from __future__ import annotations

from mcpx.descriptors.types import FieldMap, MCPSpec, SkillsSpec, ToolDescriptor, transport_field
from mcpx.update import UpdateRecipe

CLAUDE = ToolDescriptor(
    id="claude",
    display_name="Claude Code",
    config_paths={"mcp": "~/.claude.json", "skills": "~/.claude/skills"},
    fmt="json",
    update=UpdateRecipe(command=["claude", "update"]),
    skills=SkillsSpec(),  # source of truth — full SKILL.md spec
    mcp=MCPSpec(
        container_key="mcpServers",
        supports_http=True,
        fields=(
            # Claude's `type` discriminator: "stdio" | "http" (sse/ws also accepted on read).
            transport_field("type"),
            FieldMap("command", "command"),
            FieldMap("args", "args"),
            FieldMap("env", "env"),
            FieldMap("url", "url"),
            FieldMap("headers", "headers"),
        ),
    ),
)
