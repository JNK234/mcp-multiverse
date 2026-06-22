# ABOUTME: Kilo Code descriptor — MCP in VS Code globalStorage mcp_settings.json (JSON, global).
# ABOUTME: Roo/Kilo terminology: auto_approve -> alwaysAllow; disabled default; type discriminated.
from __future__ import annotations

from mcpx.descriptors.types import (
    FieldMap,
    MCPSpec,
    SkillsSpec,
    ToolDescriptor,
    vscode_globalstorage_path,
)
from mcpx.ir import Transport
from mcpx.update import UpdateRecipe

_TRANSPORT = FieldMap(
    ir_field="transport",
    native_key="type",
    to_native=lambda t: "stdio" if t is Transport.STDIO else "streamableHttp",
    from_native=lambda v: Transport.STDIO if v == "stdio" else Transport.HTTP,
)

KILO = ToolDescriptor(
    id="kilo",
    display_name="Kilo Code",
    config_paths={
        "mcp": vscode_globalstorage_path("kilocode.kilo-code", "mcp_settings.json"),
        "skills": "~/.kilo/skills",
    },
    fmt="json",
    # Kilo is a VS Code extension — update via VS Code, not a shell command.
    update=UpdateRecipe(note="Update via VS Code Extensions panel (Kilo Code auto-updates there)."),
    skills=SkillsSpec(),  # full SKILL.md spec
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
            # Kilo (like Roo) uses `alwaysAllow` — distinct from Cline's `autoApprove`.
            FieldMap("auto_approve", "alwaysAllow"),
        ),
        defaults=(("disabled", False),),
    ),
)
