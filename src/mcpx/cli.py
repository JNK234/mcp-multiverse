# ABOUTME: CLI for mcpx — IR-based port manager. Commands: import / port / list.
# ABOUTME: Claude Code is the source of truth; port pushes MCP servers to the other tools.
from __future__ import annotations

import argparse
import sys

from mcpx import __version__
from mcpx.descriptors import REGISTRY
from mcpx.engine.skills_engine import export_skills, import_skills
from mcpx.manifest import (
    get_manifest_path,
    get_skills_store_dir,
    load_manifest,
    load_skills_from_store,
    save_skills_to_store,
)
from mcpx.port import import_to_manifest, installed_targets, port
from mcpx.update import run_updates

# Exit codes: 0 = success, 1 = partial, 2 = config error, 3 = fatal.
EXIT_SUCCESS = 0
EXIT_PARTIAL = 1
EXIT_CONFIG_ERROR = 2
EXIT_FATAL = 3


def cmd_import(args: argparse.Namespace) -> int:
    """Import a source tool's MCP servers (or skills) into the IR store."""
    source = getattr(args, "source", "claude") or "claude"
    if source not in REGISTRY:
        print(f"Error: unknown source tool '{source}'. Known: {', '.join(sorted(REGISTRY))}")
        return EXIT_CONFIG_ERROR

    print(f"mcpx import v{__version__}")

    if getattr(args, "skills", False):
        skills = import_skills(REGISTRY[source])
        save_skills_to_store(skills)
        print(f"Imported {len(skills)} skill(s) from "
              f"{REGISTRY[source].display_name} into {get_skills_store_dir()}")
        for name in skills:
            print(f"  {name}")
        return EXIT_SUCCESS

    manifest = import_to_manifest(source)
    print(f"Imported {len(manifest.servers)} MCP server(s) from "
          f"{REGISTRY[source].display_name} into {get_manifest_path()}")
    for name in manifest.servers:
        print(f"  {name}")
    return EXIT_SUCCESS


def cmd_list(args: argparse.Namespace) -> int:
    """List MCP servers (or skills) currently in the IR store."""
    if getattr(args, "skills", False):
        store = get_skills_store_dir()
        skills = load_skills_from_store(store)
        if not skills:
            print(f"Error: no skills in store at {store}. Run 'mcpx import --skills' first.")
            return EXIT_CONFIG_ERROR
        print(f"Skills in {store}:")
        print()
        for name, skill in skills.items():
            desc = skill.frontmatter.get("description", "")
            extra = f" (+{len(skill.files)} files)" if skill.files else ""
            print(f"  {name:24}{extra} {desc[:60]}")
        print()
        print(f"Total: {len(skills)} skill(s)")
        return EXIT_SUCCESS

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


def _resolve_targets(args: argparse.Namespace, source: str) -> list[str] | None:
    """Resolve --to list (validated) or all installed targets. None signals a config error."""
    to_arg = getattr(args, "to", None)
    if to_arg:
        target_ids = [t.strip() for t in to_arg.split(",") if t.strip()]
        unknown = [t for t in target_ids if t not in REGISTRY]
        if unknown:
            print(f"Error: unknown target tool(s): {', '.join(unknown)}. "
                  f"Known: {', '.join(sorted(REGISTRY))}")
            return None
        return target_ids
    return installed_targets(exclude=source)


def cmd_port(args: argparse.Namespace) -> int:
    """Port MCP servers (or skills) from the store to one or more target tools."""
    source = getattr(args, "source", "claude") or "claude"
    kind = getattr(args, "kind", "mcp") or "mcp"
    dry_run = bool(getattr(args, "dry_run", False))

    target_ids = _resolve_targets(args, source)
    if target_ids is None:
        return EXIT_CONFIG_ERROR

    if kind == "skills":
        return _port_skills(source, target_ids, dry_run)
    return _port_mcp(source, target_ids, dry_run)


def _port_mcp(source: str, target_ids: list[str], dry_run: bool) -> int:
    path = get_manifest_path()
    if not path.exists():
        print(f"Error: no manifest at {path}. Run 'mcpx import' first.")
        return EXIT_CONFIG_ERROR
    manifest = load_manifest(path)

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


def _port_skills(source: str, target_ids: list[str], dry_run: bool) -> int:
    skills = load_skills_from_store(get_skills_store_dir())
    if not skills:
        print("Error: no skills in store. Run 'mcpx import --skills' first.")
        return EXIT_CONFIG_ERROR

    print(f"mcpx port v{__version__} (skills)")
    print(f"Source: {REGISTRY[source].display_name} ({len(skills)} skills)")
    if dry_run:
        print("(dry-run — no files will be written)")
    print()

    total_warnings = 0
    for tool_id in target_ids:
        if tool_id == source:
            continue
        desc = REGISTRY[tool_id]
        result = export_skills(desc, skills, dry_run=dry_run)
        verb = "would write" if dry_run else "wrote"
        print(f"  {desc.display_name}: {verb} {len(result.written)} skill(s)")
        for warning in result.warnings:
            print(f"    ! {warning}")
        total_warnings += len(result.warnings)

    print()
    summary = "Dry-run complete" if dry_run else "Skills port complete"
    print(f"{summary}: {len(target_ids)} tool(s), {total_warnings} warning(s)")
    return EXIT_PARTIAL if total_warnings else EXIT_SUCCESS


def cmd_update(args: argparse.Namespace) -> int:
    """Update all installed CLI tools via their declarative update recipes."""
    print(f"mcpx update v{__version__}")
    print("Updating installed CLI tools...")
    print()

    # Print each command before running it (traceability), then run.
    descriptors = list(REGISTRY.values())
    for desc in descriptors:
        recipe = desc.update
        if recipe and recipe.command:
            print(f"  $ {' '.join(recipe.command)}   ({desc.display_name})")
    print()

    results = run_updates(descriptors)

    updated = failed = 0
    for r in results:
        if r.ran and r.ok:
            print(f"  ✓ {r.display_name}: {r.message}")
            updated += 1
        elif r.ran and not r.ok:
            print(f"  ✗ {r.display_name}: {r.message}")
            failed += 1
        else:
            print(f"  · {r.display_name}: {r.message}")

    print()
    print(f"Update complete: {updated} updated, {failed} failed.")
    return EXIT_PARTIAL if failed else EXIT_SUCCESS


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse CLI."""
    parser = argparse.ArgumentParser(
        prog="mcpx",
        description="Port MCP servers across AI coding tools (Claude Code as source).",
    )
    parser.add_argument("--version", "-V", action="version", version=f"mcpx v{__version__}")
    sub = parser.add_subparsers(dest="command")

    p_import = sub.add_parser("import", help="Import a tool's MCP servers or skills")
    p_import.add_argument("--source", "--from", dest="source", default="claude",
                          help="Source tool id (default: claude)")
    p_import.add_argument("--skills", action="store_true",
                          help="Import skills instead of MCP servers")

    p_list = sub.add_parser("list", help="List MCP servers or skills in the store")
    p_list.add_argument("--skills", action="store_true", help="List skills instead of servers")

    p_port = sub.add_parser("port", help="Port MCP servers or skills to target tools")
    p_port.add_argument("--source", "--from", dest="source", default="claude",
                        help="Source tool id (default: claude)")
    p_port.add_argument("--to", help="Comma-separated target tool ids (default: all installed)")
    p_port.add_argument("--kind", choices=["mcp", "skills"], default="mcp",
                        help="What to port (default: mcp)")
    p_port.add_argument("--dry-run", action="store_true",
                        help="Show what would be written without writing")
    p_port.add_argument("--yes", "-y", action="store_true",
                        help="Write without confirmation prompt")

    sub.add_parser("update", help="Update all installed CLI tools to their latest versions")
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
    if args.command == "update":
        return cmd_update(args)

    parser.print_help()
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
