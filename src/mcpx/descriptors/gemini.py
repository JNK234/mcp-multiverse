# ABOUTME: Gemini CLI descriptor — MCP in ~/.gemini/settings.json under mcpServers (JSON).
# ABOUTME: Foreign keys (selectedAuthType, theme) survive: the engine only rewrites mcpServers.
from __future__ import annotations

from mcpx.descriptors.types import (
    FieldMap,
    MCPSpec,
    SkillsSpec,
    ToolDescriptor,
    transport_field,
)
from mcpx.update import UpdateRecipe

GEMINI = ToolDescriptor(
    id="gemini",
    display_name="Gemini CLI",
    config_paths={"mcp": "~/.gemini/settings.json", "skills": "~/.gemini/skills"},
    fmt="json",
    # Gemini has no self-update subcommand; it's distributed via npm.
    update=UpdateRecipe(command=["npm", "install", "-g", "@google/gemini-cli@latest"]),
    skills=SkillsSpec(),  # full SKILL.md spec (incl. allowed-tools)
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
