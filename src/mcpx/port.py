# ABOUTME: Port orchestrator — import MCP servers from a source tool into the IR, export to targets.
# ABOUTME: Both directions flow through the persisted manifest (the IR hub).
from __future__ import annotations

from dataclasses import dataclass, field

from mcpx.descriptors import REGISTRY, get_descriptor
from mcpx.engine import ExportResult, export_mcp, import_mcp
from mcpx.ir import Manifest, MCPServerIR
from mcpx.manifest import MANIFEST_VERSION, save_manifest


@dataclass
class PortReport:
    """Result of a port run across one or more targets."""

    source_id: str
    servers: dict[str, MCPServerIR] = field(default_factory=dict)
    results: list[ExportResult] = field(default_factory=list)

    @property
    def warnings(self) -> list[str]:
        return [w for r in self.results for w in r.warnings]


def installed_targets(exclude: str | None = None) -> list[str]:
    """Return ids of tools whose config directory exists (treated as 'installed').

    ABOUTME: Probes the parent dir of each descriptor's MCP path; excludes the source.
    """
    found: list[str] = []
    for tool_id, desc in REGISTRY.items():
        if tool_id == exclude or desc.mcp is None:
            continue
        from mcpx.engine.mcp_engine import resolve_path

        if resolve_path(desc).parent.exists():
            found.append(tool_id)
    return found


def import_to_manifest(source_id: str) -> Manifest:
    """Import the source tool's MCP servers into a fresh Manifest and persist it.

    ABOUTME: The manifest becomes the authoritative IR set for subsequent exports.
    """
    desc = get_descriptor(source_id)
    servers = import_mcp(desc)
    manifest = Manifest(version=MANIFEST_VERSION, servers=servers)
    save_manifest(manifest)
    return manifest


def port(
    servers: dict[str, MCPServerIR],
    target_ids: list[str],
    *,
    source_id: str = "claude",
    dry_run: bool = False,
) -> PortReport:
    """Export IR servers to each target tool.

    ABOUTME: Skips a target that is the source itself; collects per-target ExportResults.
    """
    report = PortReport(source_id=source_id, servers=servers)
    for tool_id in target_ids:
        if tool_id == source_id:
            continue
        desc = get_descriptor(tool_id)
        report.results.append(export_mcp(desc, servers, dry_run=dry_run))
    return report
