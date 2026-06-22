# ABOUTME: CLI for mcpx — IR-based port manager. Commands: import / port / list.
# ABOUTME: Claude Code is the source of truth; port pushes MCP servers to the other tools.
from __future__ import annotations

import argparse
import sys

from mcpx import __version__
from mcpx.descriptors import REGISTRY
from mcpx.manifest import get_manifest_path, load_manifest
from mcpx.port import import_to_manifest, installed_targets, port

# Exit codes: 0 = success, 1 = partial, 2 = config error, 3 = fatal.
EXIT_SUCCESS = 0
EXIT_PARTIAL = 1
EXIT_CONFIG_ERROR = 2
EXIT_FATAL = 3


def cmd_import(args: argparse.Namespace) -> int:
    """Import a source tool's MCP servers into the IR manifest (~/.mcpx/manifest.json)."""
    source = getattr(args, "source", "claude") or "claude"
    if source not in REGISTRY:
        print(f"Error: unknown source tool '{source}'. Known: {', '.join(sorted(REGISTRY))}")
        return EXIT_CONFIG_ERROR

    manifest = import_to_manifest(source)
    print(f"mcpx import v{__version__}")
    print(f"Imported {len(manifest.servers)} MCP server(s) from "
          f"{REGISTRY[source].display_name} into {get_manifest_path()}")
    for name in manifest.servers:
        print(f"  {name}")
    return EXIT_SUCCESS


def cmd_list(args: argparse.Namespace) -> int:
    """List MCP servers currently in the IR manifest."""
    path = get_manifest_path()
    if not path.exists():
        print(f"Error: no manifest at {path}. Run 'mcpx import' first.")
        return EXIT_CONFIG_ERROR

    manifest = load_manifest(path)
    print(f"MCP servers in {path}:")
    print()
    for name, server in manifest.servers.items():
        detail = server.command if server.command else server.url
        print(f"  {name:24} [{server.transport.value}] {detail}")
    print()
    print(f"Total: {len(manifest.servers)} server(s)")
    return EXIT_SUCCESS


def cmd_port(args: argparse.Namespace) -> int:
    """Port MCP servers from the manifest to one or more target tools."""
    source = getattr(args, "source", "claude") or "claude"
    path = get_manifest_path()
    if not path.exists():
        print(f"Error: no manifest at {path}. Run 'mcpx import' first.")
        return EXIT_CONFIG_ERROR

    manifest = load_manifest(path)

    # Resolve targets: explicit --to list, or all installed tools (minus the source).
    to_arg = getattr(args, "to", None)
    if to_arg:
        target_ids = [t.strip() for t in to_arg.split(",") if t.strip()]
        unknown = [t for t in target_ids if t not in REGISTRY]
        if unknown:
            print(f"Error: unknown target tool(s): {', '.join(unknown)}. "
                  f"Known: {', '.join(sorted(REGISTRY))}")
            return EXIT_CONFIG_ERROR
    else:
        target_ids = installed_targets(exclude=source)

    dry_run = bool(getattr(args, "dry_run", False))
    print(f"mcpx port v{__version__}")
    print(f"Source: {REGISTRY[source].display_name} ({len(manifest.servers)} servers)")
    if dry_run:
        print("(dry-run — no files will be written)")
    print()

    report = port(manifest.servers, target_ids, source_id=source, dry_run=dry_run)

    for result in report.results:
        desc = REGISTRY[result.tool_id]
        verb = "would write" if dry_run else "wrote"
        print(f"  {desc.display_name}: {verb} {len(result.written)} server(s)"
              + (f", skipped {len(result.skipped)}" if result.skipped else ""))
        for warning in result.warnings:
            print(f"    ! {warning}")

    print()
    total_warnings = len(report.warnings)
    summary = "Dry-run complete" if dry_run else "Port complete"
    print(f"{summary}: {len(report.results)} tool(s), {total_warnings} warning(s)")
    return EXIT_PARTIAL if total_warnings else EXIT_SUCCESS


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse CLI."""
    parser = argparse.ArgumentParser(
        prog="mcpx",
        description="Port MCP servers across AI coding tools (Claude Code as source).",
    )
    parser.add_argument("--version", "-V", action="version", version=f"mcpx v{__version__}")
    sub = parser.add_subparsers(dest="command")

    p_import = sub.add_parser("import", help="Import a tool's MCP servers into the manifest")
    p_import.add_argument("--source", "--from", dest="source", default="claude",
                          help="Source tool id (default: claude)")

    sub.add_parser("list", help="List MCP servers in the manifest")

    p_port = sub.add_parser("port", help="Port manifest MCP servers to target tools")
    p_port.add_argument("--source", "--from", dest="source", default="claude",
                        help="Source tool id (default: claude)")
    p_port.add_argument("--to", help="Comma-separated target tool ids (default: all installed)")
    p_port.add_argument("--dry-run", action="store_true",
                        help="Show what would be written without writing")
    p_port.add_argument("--yes", "-y", action="store_true",
                        help="Write without confirmation prompt")
    return parser


def main() -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "import":
        return cmd_import(args)
    if args.command == "list":
        return cmd_list(args)
    if args.command == "port":
        return cmd_port(args)

    parser.print_help()
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
