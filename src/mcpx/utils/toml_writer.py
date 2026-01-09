# Minimal TOML writer for mcpx
from pathlib import Path
from typing import Any


def write_toml_simple(data: dict[str, Any], path: Path) -> None:
    """Write simple TOML format for Codex CLI config.

    ABOUTME: Minimal TOML writer handling only our subset (command, args, env)
    ABOUTME: Writes nested tables for mcp_servers with proper array formatting

    Args:
        data: Dictionary with mcp_servers key containing server configs
        path: Output file path (will create parent dirs)

    Example output:
        [mcp_servers.filesystem]
        command = "npx"
        args = ["-y", "@modelcontextprotocol/server-filesystem", "/path"]

        [mcp_servers.github]
        command = "npx"
        args = ["-y", "@modelcontextprotocol/server-github"]
        env = { GITHUB_TOKEN = "ghp_xxxx" }
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    # Extract mcp_servers section
    mcp_servers = data.get("mcp_servers", {})

    for server_name, server_config in mcp_servers.items():
        # Write section header
        lines.append(f"[mcp_servers.{server_name}]")

        # Write command (required) - escape special characters
        command = server_config.get("command", "")
        escaped_command = command.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'command = "{escaped_command}"')

        # Write args array
        args = server_config.get("args", [])
        if args:
            args_formatted = _format_array(args)
            lines.append(f"args = {args_formatted}")

        # Write env table if present
        env = server_config.get("env", {})
        if env:
            env_formatted = _format_inline_table(env)
            lines.append(f"env = {env_formatted}")

        # Add blank line between servers
        lines.append("")

    # Write to file
    toml_content = "\n".join(lines).rstrip() + "\n"
    path.write_text(toml_content, encoding="utf-8")


def _format_array(items: list[Any]) -> str:
    """Format list as TOML array.

    ABOUTME: Converts Python list to ["item1", "item2"] format
    ABOUTME: Handles strings with special characters
    """
    if not items:
        return "[]"

    formatted_items = []
    for item in items:
        # Escape quotes and backslashes in strings
        if isinstance(item, str):
            escaped = item.replace("\\", "\\\\").replace('"', '\\"')
            formatted_items.append(f'"{escaped}"')
        else:
            formatted_items.append(str(item))

    return "[" + ", ".join(formatted_items) + "]"


def _format_inline_table(data: dict[str, str]) -> str:
    """Format dict as TOML inline table.

    ABOUTME: Converts {"KEY": "value"} to { KEY = "value" } format
    ABOUTME: Used for env variables in Codex config
    """
    if not data:
        return "{}"

    pairs = []
    for key, value in data.items():
        # Escape quotes and backslashes in values
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        pairs.append(f'{key} = "{escaped}"')

    return "{ " + ", ".join(pairs) + " }"
