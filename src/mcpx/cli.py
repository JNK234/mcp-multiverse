# CLI interface for mcpx
import argparse
import os
import re
import shutil
import sys

from mcpx import __version__
from mcpx.config import get_config_path, load_config
from mcpx.init import cmd_init
from mcpx.sync import sync_all
from mcpx.utils import validate_server

# ABOUTME: Exit codes per spec
# 0 = success, 1 = partial success, 2 = config error, 3 = fatal
EXIT_SUCCESS = 0
EXIT_PARTIAL = 1
EXIT_CONFIG_ERROR = 2
EXIT_FATAL = 3


def cmd_sync(args: argparse.Namespace) -> int:
    """Execute sync command.

    ABOUTME: Loads config, validates, syncs to all platforms
    ABOUTME: Triggers first-run init if config doesn't exist
    ABOUTME: Returns exit code based on results
    """
    from mcpx.sync import first_run_init

    # Print header
    print(f"mcpx sync v{__version__}")

    try:
        # Get config path
        config_path = get_config_path()

        # Check if config exists
        if not config_path.exists():
            print()
            print("No config found. Creating ~/.mcpx/config.json...")
            print()
            # Run first-run initialization
            first_report = first_run_init()
            print()
            msg = (
                f"Generated config with {first_report.server_count} "
                f"unique server(s) (deduplicated)."
            )
            print(msg)
            print(f"Edit {config_path} to customize, then run 'mcpx sync' again.")
            print()
            return EXIT_SUCCESS

        print(f"Loading config from {config_path}")
        config = load_config(config_path)

        # Show servers found
        server_count = len(config.servers)
        server_names = ", ".join(config.servers.keys())
        print(f"Found {server_count} MCP server(s): {server_names}")
        print()

        # Validate commands
        print("Validating commands...")
        has_errors = False
        for server_name, server in config.servers.items():
            errors = validate_server(server)
            for error in errors:
                if error.severity == "error":
                    print(f"  Server '{server_name}': {error.message}")
                    has_errors = True
                else:
                    print(f"  Warning: {error.message}")

        if has_errors:
            print()
            print("Config validation failed. Fix errors above and try again.")
            return EXIT_CONFIG_ERROR

        # Count unique commands for summary
        commands = {s.command for s in config.servers.values()}
        for cmd in commands:
            print(f"  {cmd} found")

        print()
        print("Syncing to platforms...")

        # Perform sync
        report = sync_all(config)

        # Print results
        for platform_name, count in report.servers_synced.items():
            if count > 0:
                print(f"  {platform_name} - {count} servers synced")
            else:
                print(f"  {platform_name} - failed")

        # Print errors if any
        if report.errors:
            print()
            for error_msg in report.errors:
                print(f"  Error: {error_msg}")

        print()
        # Determine exit code
        if report.errors:
            msg = (
                f"Sync complete: {report.platforms_synced}/"
                f"{report.platforms_total} platforms updated, "
                f"{len(report.errors)} failed"
            )
            print(msg)
            return EXIT_PARTIAL
        else:
            msg = (
                f"Sync complete: {report.platforms_synced}/"
                f"{report.platforms_total} platforms updated"
            )
            print(msg)
            return EXIT_SUCCESS

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print()
        print("Config file not found. Create one at ~/.mcpx/config.json")
        return EXIT_CONFIG_ERROR
    except Exception as e:
        print(f"Fatal error: {e}")
        return EXIT_FATAL


def cmd_list(args: argparse.Namespace) -> int:
    """Execute list command.

    ABOUTME: Loads config and displays all servers
    ABOUTME: Returns exit code based on success/failure
    """
    # Print header
    print(f"mcpx list v{__version__}")
    print()

    try:
        # Get and load config
        config_path = get_config_path()
        config = load_config(config_path)

        print(f"MCP Servers in {config_path}:")
        print()

        # List each server
        for server_name, server in config.servers.items():
            print(f"  {server_name}")
            print(f"    type: {server.type}")

            if server.type == "stdio":
                print(f"    command: {server.command}")

                if server.args:
                    args_str = " ".join(server.args)
                    print(f"    args: {args_str}")

                if server.env:
                    env_str = ", ".join(f"{k}={v}" for k, v in server.env.items())
                    print(f"    env: {env_str}")
            elif server.type == "http":
                if server.url:
                    print(f"    url: {server.url}")

                if server.headers:
                    headers_str = ", ".join(f"{k}={v}" for k, v in server.headers.items())
                    print(f"    headers: {headers_str}")

            print()

        print(f"Total: {len(config.servers)} server(s)")
        return EXIT_SUCCESS

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print()
        print("Config file not found. Create one at ~/.mcpx/config.json")
        return EXIT_CONFIG_ERROR
    except Exception as e:
        print(f"Fatal error: {e}")
        return EXIT_FATAL


def cmd_validate(args: argparse.Namespace) -> int:
    """Execute validate command.

    ABOUTME: Loads config and validates without modifying files
    ABOUTME: Performs full validation per spec section 5.2
    ABOUTME: Returns exit code based on validation results
    """
    import shutil

    # Print header
    print(f"mcpx validate v{__version__}")
    print()

    try:
        # Get and load config
        config_path = get_config_path()
        print(f"Validating {config_path}...")
        print()

        config = load_config(config_path)

        print("  ✓ JSON syntax valid")
        print(f"  ✓ {len(config.servers)} server(s) defined")
        print()

        # Separate stdio and HTTP servers for validation
        stdio_servers = {name: s for name, s in config.servers.items() if s.type == "stdio"}
        http_servers = {name: s for name, s in config.servers.items() if s.type == "http"}

        # Check stdio servers
        if stdio_servers:
            print("  Checking stdio servers:")
            commands = {server.command for server in stdio_servers.values() if server.command}
            command_errors = 0
            for cmd in sorted(commands):
                cmd_path = shutil.which(cmd)
                if cmd_path:
                    print(f"    ✓ {cmd} -> {cmd_path}")
                else:
                    print(f"    ✗ {cmd} not found")
                    command_errors += 1

        # Check HTTP servers
        if http_servers:
            print()
            print("  Checking HTTP servers:")
            for server_name, server in http_servers.items():
                if server.url:
                    print(f"    ✓ {server_name}: {server.url}")

        # Check environment variables
        env_warnings = 0
        env_references: dict[str, set[str]] = {}  # var_name -> server_names

        for server_name, server in config.servers.items():
            if server.type == "stdio" and server.command:
                # Check in command
                for match in re.finditer(r'\$\{([A-Z_][A-Z0-9_]*)\}', server.command):
                    var_name = match.group(1)
                    if var_name not in env_references:
                        env_references[var_name] = set()
                    env_references[var_name].add(server_name)

                # Check in args
                for arg in server.args:
                    for match in re.finditer(r'\$\{([A-Z_][A-Z0-9_]*)\}', arg):
                        var_name = match.group(1)
                        if var_name not in env_references:
                            env_references[var_name] = set()
                        env_references[var_name].add(server_name)

                # Check in env values
                for _key, value in server.env.items():
                    for match in re.finditer(r'\$\{([A-Z_][A-Z0-9_]*)\}', value):
                        var_name = match.group(1)
                        if var_name not in env_references:
                            env_references[var_name] = set()
                        env_references[var_name].add(server_name)
            elif server.type == "http" and server.url:
                # Check in URL
                for match in re.finditer(r'\$\{([A-Z_][A-Z0-9_]*)\}', server.url):
                    var_name = match.group(1)
                    if var_name not in env_references:
                        env_references[var_name] = set()
                    env_references[var_name].add(server_name)

                # Check in headers
                for _key, value in server.headers.items():
                    for match in re.finditer(r'\$\{([A-Z_][A-Z0-9_]*)\}', value):
                        var_name = match.group(1)
                        if var_name not in env_references:
                            env_references[var_name] = set()
                        env_references[var_name].add(server_name)

        # Print environment variable checks
        if env_references:
            print()
            print("  Checking environment variables:")
            for var_name, server_names in sorted(env_references.items()):
                if var_name in os.environ:
                    print(f"    ✓ ${var_name} -> {os.environ[var_name]}")
                else:
                    servers_str = ", ".join(sorted(server_names))
                    print(f"    ⚠ ${{{var_name}}} not set (server: {servers_str})")
                    env_warnings += 1

        # Summary
        print()
        command_errors = sum(1 for s in stdio_servers.values() if s.command and not shutil.which(s.command))
        print(f"Validation complete: {command_errors} error(s), {env_warnings} warning(s)")

        if command_errors > 0:
            return EXIT_CONFIG_ERROR
        else:
            return EXIT_SUCCESS

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print()
        print("Config file not found. Create one at ~/.mcpx/config.json")
        return EXIT_CONFIG_ERROR
    except Exception as e:
        print(f"Fatal error: {e}")
        return EXIT_FATAL


def main() -> int:
    """Main CLI entry point.

    ABOUTME: Parses args and dispatches to appropriate command
    ABOUTME: Returns exit code for sys.exit()
    """
    parser = argparse.ArgumentParser(
        prog="mcpx",
        description="Universal MCP server sync manager for AI coding assistants"
    )

    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"mcpx v{__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # sync command
    subparsers.add_parser(
        "sync",
        help="Sync global config to all platforms"
    )

    # list command
    subparsers.add_parser(
        "list",
        help="List all MCPs in source config"
    )

    # validate command
    subparsers.add_parser(
        "validate",
        help="Validate config without syncing"
    )

    # init command
    subparsers.add_parser(
        "init",
        help="Initialize project-level MCP configuration"
    )

    # Parse args
    args = parser.parse_args()

    # Dispatch to command
    if args.command == "sync":
        return cmd_sync(args)
    elif args.command == "list":
        return cmd_list(args)
    elif args.command == "validate":
        return cmd_validate(args)
    elif args.command == "init":
        return cmd_init()
    else:
        # No command specified, show help
        parser.print_help()
        return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
