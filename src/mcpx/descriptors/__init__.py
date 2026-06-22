# ABOUTME: Registry of all tool descriptors — add a tool by dropping its descriptor in here.
# ABOUTME: The engine resolves tools from REGISTRY; no engine code changes per tool.
from mcpx.descriptors.claude import CLAUDE
from mcpx.descriptors.cline import CLINE
from mcpx.descriptors.codex import CODEX
from mcpx.descriptors.gemini import GEMINI
from mcpx.descriptors.kilo import KILO
from mcpx.descriptors.opencode import OPENCODE
from mcpx.descriptors.types import FieldMap, MCPSpec, ToolDescriptor

REGISTRY: dict[str, ToolDescriptor] = {
    d.id: d for d in (CLAUDE, GEMINI, CODEX, OPENCODE, CLINE, KILO)
}

__all__ = ["REGISTRY", "ToolDescriptor", "MCPSpec", "FieldMap"]


def get_descriptor(tool_id: str) -> ToolDescriptor:
    """Return a tool descriptor by id, or raise KeyError with the known ids."""
    try:
        return REGISTRY[tool_id]
    except KeyError:
        known = ", ".join(sorted(REGISTRY))
        raise KeyError(f"Unknown tool '{tool_id}'. Known: {known}") from None
