# ABOUTME: Generic MCP import/export engine — drives porting off ToolDescriptor data alone.
# ABOUTME: import_mcp (tool->IR) and export_mcp (IR->tool) work for any tool with zero branches.
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mcpx.codecs import codec_for
from mcpx.descriptors.types import ToolDescriptor
from mcpx.engine.mapping import apply_field_maps_to_ir, render_native_from_ir
from mcpx.ir import MCPServerIR, Transport
from mcpx.utils.backup import create_backup, get_backup_dir


@dataclass
class ExportResult:
    """Outcome of exporting servers to one tool.

    ABOUTME: written = native server dicts that would be / were written (for diff + dry-run).
    ABOUTME: warnings = human-readable lossy/skip notes sourced from descriptor data only.
    """

    tool_id: str
    path: Path
    written: dict[str, dict[str, Any]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def resolve_path(desc: ToolDescriptor, logical: str = "mcp") -> Path:
    """Expand a descriptor's config path template (handles ~)."""
    return Path(desc.config_paths[logical]).expanduser()


def import_mcp(desc: ToolDescriptor) -> dict[str, MCPServerIR]:
    """Parse a tool's native config into canonical IR servers.

    ABOUTME: Returns {} if the tool has no MCP support or its config file is absent.
    """
    if desc.mcp is None:
        return {}
    path = resolve_path(desc)
    if not path.exists():
        return {}
    raw = codec_for(desc.fmt).read(path)
    container = raw.get(desc.mcp.container_key, {})
    return {
        name: apply_field_maps_to_ir(desc.mcp, desc.id, name, native)
        for name, native in container.items()
    }


def export_mcp(
    desc: ToolDescriptor,
    servers: dict[str, MCPServerIR],
    *,
    dry_run: bool = False,
) -> ExportResult:
    """Render IR servers into a tool's native config and (unless dry_run) write it.

    ABOUTME: Backs up the existing file first (labeled by tool id). HTTP servers going to a
    ABOUTME: tool with supports_http=False are skipped with a warning, never silently dropped.
    ABOUTME: preserve_orphans (off this cut) would keep unmanaged servers already in the file.
    """
    path = resolve_path(desc)
    result = ExportResult(tool_id=desc.id, path=path)

    if desc.mcp is None:
        result.warnings.append(f"{desc.display_name}: no MCP support — skipped")
        return result

    spec = desc.mcp
    rendered: dict[str, dict[str, Any]] = {}
    for name, server in servers.items():
        if server.transport is Transport.HTTP and not spec.supports_http:
            result.skipped.append(name)
            result.warnings.append(
                f"{desc.display_name}: '{name}' is an HTTP server but "
                f"{desc.display_name} has no HTTP MCP support — skipped"
            )
            continue
        rendered[name] = render_native_from_ir(spec, desc.id, server)

    result.written = rendered

    if dry_run:
        return result

    codec = codec_for(desc.fmt)
    existing = codec.read(path) if path.exists() else {}

    container = dict(existing.get(spec.container_key, {})) if spec.preserve_orphans else {}
    container.update(rendered)
    existing[spec.container_key] = container

    if path.exists():
        create_backup(path, get_backup_dir(), label=desc.id)
    codec.write(path, existing)
    return result
