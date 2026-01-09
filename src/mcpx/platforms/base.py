# Platform adapter base utilities
import json
from pathlib import Path
from typing import Any, cast

from mcpx.models import MCPServer


def read_json_file(path: Path) -> dict[str, Any]:
    """Read JSON file with error handling.

    ABOUTME: Returns empty dict if file doesn't exist
    ABOUTME: Raises ValueError for invalid JSON
    """
    if not path.exists():
        return {}

    try:
        with open(path, encoding="utf-8") as f:
            result = json.load(f)
            return cast(dict[str, Any], result)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}") from e


def write_json_file(path: Path, data: dict[str, Any]) -> None:
    """Write JSON file with error handling.

    ABOUTME: Creates parent directories if needed
    ABOUTME: Uses 2-space indentation for readability
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")  # Add trailing newline


def server_to_dict(server: MCPServer) -> dict[str, Any]:
    """Convert MCPServer to platform dict format.

    ABOUTME: Converts dataclass to dict for JSON serialization
    ABOUTME: Omits empty env dict for cleaner output
    ABOUTME: Handles both stdio and HTTP server types
    """
    result: dict[str, Any] = {
        "type": server.type,
    }

    if server.type == "stdio":
        result["command"] = server.command
        result["args"] = server.args
        if server.env:
            result["env"] = server.env
    elif server.type == "http":
        if server.url:
            result["url"] = server.url
        if server.headers:
            result["headers"] = server.headers

    return result


def dict_to_server(name: str, data: dict[str, Any]) -> MCPServer:
    """Convert platform dict format to MCPServer.

    ABOUTME: Handles missing env field gracefully
    ABOUTME: Validates required command field for stdio servers
    ABOUTME: Supports both stdio and HTTP server types
    """
    server_type = data.get("type", "stdio")

    if server_type == "stdio":
        if "command" not in data:
            raise ValueError(f"Server '{name}' missing required 'command' field")

        return MCPServer(
            name=name,
            type="stdio",
            command=data["command"],
            args=data.get("args", []),
            env=data.get("env", {}),
        )
    elif server_type == "http":
        if "url" not in data:
            raise ValueError(f"Server '{name}' missing required 'url' field for http type")

        return MCPServer(
            name=name,
            type="http",
            url=data["url"],
            headers=data.get("headers", {}),
        )
    else:
        raise ValueError(
            f"Server '{name}' has invalid type '{server_type}'. Must be 'stdio' or 'http'."
        )
