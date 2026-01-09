# CLI interface for mcpx
import argparse
import os
import re
import shutil
import sys

from mcpx import __version__
from mcpx.config import (
    add_server_to_config,
    get_config_path,
    load_config,
    remove_server_from_config,
)
from mcpx.models import MCPServer
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


def cmd_add(args: argparse.Namespace) -> int:
    """Execute add command.

    ABOUTME: Adds a new MCP server to config
    ABOUTME: Interactive mode prompts for server details
    ABOUTME: Non-interactive mode uses command-line args
    ABOUTME: Syncs to all platforms after adding
    """
    print(f"mcpx add v{__version__}")
    print()

    server_name = args.name

    # Check if server already exists
    config_path = get_config_path()
    try:
        if config_path.exists():
            config = load_config(config_path)
            if server_name in config.servers:
                print(f"Warning: Server '{server_name}' already exists. It will be replaced.")
                print()
    except (ValueError, FileNotFoundError):
        pass  # Config doesn't exist or is invalid, will be created

    # Determine if interactive or non-interactive mode
    if args.type:
        # Non-interactive mode
        server_type = args.type
        command = args.command
        url = args.url
        server_args = args.args.split(",") if args.args else []
        env_vars: dict[str, str] = {}
        headers: dict[str, str] = {}

        # Parse env vars (KEY=VALUE format)
        if args.env:
            for env_pair in args.env.split(","):
                if "=" in env_pair:
                    key, value = env_pair.split("=", 1)
                    env_vars[key.strip()] = value.strip()

        # Parse headers (KEY=VALUE format)
        if args.headers:
            for header_pair in args.headers.split(","):
                if "=" in header_pair:
                    key, value = header_pair.split("=", 1)
                    headers[key.strip()] = value.strip()

    else:
        # Interactive mode
        print(f"Adding new MCP server: {server_name}")
        print()

        # Prompt for type
        while True:
            server_type = input("Type (stdio/http) [stdio]: ").strip().lower() or "stdio"
            if server_type in ("stdio", "http"):
                break
            print("  Invalid type. Please enter 'stdio' or 'http'.")

        command = None
        url = None
        server_args = []
        env_vars = {}
        headers = {}

        if server_type == "stdio":
            # Prompt for command
            command = input("Command (e.g., npx, node, python): ").strip()
            if not command:
                print("Error: Command is required for stdio servers.")
                return EXIT_CONFIG_ERROR

            # Prompt for args
            args_input = input("Arguments (comma-separated, e.g., -y,@mcp/package): ").strip()
            if args_input:
                server_args = [arg.strip() for arg in args_input.split(",")]

            # Prompt for env vars
            print("Environment variables (KEY=VALUE, one per line, empty line to finish):")
            while True:
                env_input = input("  ").strip()
                if not env_input:
                    break
                if "=" in env_input:
                    key, value = env_input.split("=", 1)
                    env_vars[key.strip()] = value.strip()
                else:
                    print("    Invalid format. Use KEY=VALUE.")

        else:  # http
            # Prompt for URL
            url = input("URL (e.g., https://api.example.com/mcp): ").strip()
            if not url:
                print("Error: URL is required for HTTP servers.")
                return EXIT_CONFIG_ERROR

            # Prompt for headers
            print("Headers (KEY=VALUE, one per line, empty line to finish):")
            while True:
                header_input = input("  ").strip()
                if not header_input:
                    break
                if "=" in header_input:
                    key, value = header_input.split("=", 1)
                    headers[key.strip()] = value.strip()
                else:
                    print("    Invalid format. Use KEY=VALUE.")

    # Create server object
    if server_type == "stdio":
        if not command:
            print("Error: Command is required for stdio servers.")
            return EXIT_CONFIG_ERROR
        server = MCPServer(
            name=server_name,
            type="stdio",
            command=command,
            args=server_args,
            env=env_vars,
        )
    else:  # http
        if not url:
            print("Error: URL is required for HTTP servers.")
            return EXIT_CONFIG_ERROR
        server = MCPServer(
            name=server_name,
            type="http",
            url=url,
            headers=headers,
        )

    print()
    print(f"Adding server '{server_name}'...")

    try:
        # Add to config
        add_server_to_config(config_path, server)
        print(f"  Added to {config_path}")

        # Sync to all platforms
        print()
        print("Syncing to platforms...")
        config = load_config(config_path)
        report = sync_all(config)

        # Print results
        for platform_name, count in report.servers_synced.items():
            if count > 0:
                print(f"  {platform_name} - {count} servers synced")
            else:
                print(f"  {platform_name} - failed")

        if report.errors:
            print()
            for error_msg in report.errors:
                print(f"  Error: {error_msg}")

        print()
        if report.errors:
            print(f"Server '{server_name}' added with partial sync.")
            return EXIT_PARTIAL
        else:
            print(f"Server '{server_name}' added and synced to all platforms.")
            return EXIT_SUCCESS

    except Exception as e:
        print(f"Fatal error: {e}")
        return EXIT_FATAL


def cmd_remove(args: argparse.Namespace) -> int:
    """Execute remove command.

    ABOUTME: Removes an MCP server from config by name
    ABOUTME: Syncs removal to all platforms
    """
    print(f"mcpx remove v{__version__}")
    print()

    server_name = args.name
    config_path = get_config_path()

    print(f"Removing server '{server_name}'...")

    try:
        # Remove from config
        removed = remove_server_from_config(config_path, server_name)

        if not removed:
            print(f"  Server '{server_name}' not found in config.")
            return EXIT_CONFIG_ERROR

        print(f"  Removed from {config_path}")

        # Sync to all platforms
        print()
        print("Syncing to platforms...")
        config = load_config(config_path)
        report = sync_all(config)

        # Print results
        for platform_name, count in report.servers_synced.items():
            if count > 0:
                print(f"  {platform_name} - {count} servers synced")
            else:
                print(f"  {platform_name} - failed")

        if report.errors:
            print()
            for error_msg in report.errors:
                print(f"  Error: {error_msg}")

        print()
        if report.errors:
            print(f"Server '{server_name}' removed with partial sync.")
            return EXIT_PARTIAL
        else:
            print(f"Server '{server_name}' removed and synced to all platforms.")
            return EXIT_SUCCESS

    except FileNotFoundError:
        print(f"Error: Config file not found at {config_path}")
        print()
        print("Run 'mcpx sync' first to create a config.")
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

    # add command
    add_parser = subparsers.add_parser(
        "add",
        help="Add a new MCP server to config"
    )
    add_parser.add_argument(
        "name",
        help="Name of the MCP server to add"
    )
    add_parser.add_argument(
        "--type",
        choices=["stdio", "http"],
        help="Server type (stdio or http)"
    )
    add_parser.add_argument(
        "--command",
        help="Command to run (for stdio type)"
    )
    add_parser.add_argument(
        "--url",
        help="URL endpoint (for http type)"
    )
    add_parser.add_argument(
        "--args",
        help="Comma-separated arguments (for stdio type)"
    )
    add_parser.add_argument(
        "--env",
        help="Comma-separated KEY=VALUE environment variables"
    )
    add_parser.add_argument(
        "--headers",
        help="Comma-separated KEY=VALUE headers (for http type)"
    )

    # remove command
    remove_parser = subparsers.add_parser(
        "remove",
        help="Remove an MCP server from config"
    )
    remove_parser.add_argument(
        "name",
        help="Name of the MCP server to remove"
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
    elif args.command == "add":
        return cmd_add(args)
    elif args.command == "remove":
        return cmd_remove(args)
    else:
        # No command specified, show help
        parser.print_help()
        return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
