# Configuration loading and parsing for mcpx
import json
from pathlib import Path

from mcpx.models import Config, MCPServer
from mcpx.utils import expand_env_vars

# ABOUTME: Default config directory in user's home
CONFIG_DIR = Path.home() / ".mcpx"

# ABOUTME: Main config file location (JSON format)
CONFIG_FILE = CONFIG_DIR / "config.json"


def get_config_path() -> Path:
    """Return the path to the mcpx config file.

    ABOUTME: Returns ~/.mcpx/config.json
    ABOUTME: File may not exist yet - use ensure_config_dir() first

    Returns:
        Path to config file
    """
    return CONFIG_FILE


def ensure_config_dir() -> Path:
    """Create config directory if it doesn't exist.

    ABOUTME: Creates ~/.mcpx/ if missing
    ABOUTME: Returns path to config directory

    Returns:
        Path to config directory (guaranteed to exist)
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def load_config(path: Path) -> Config:
    """Load and parse mcpx config from JSON file.

    ABOUTME: Uses built-in json module for JSON parsing
    ABOUTME: Fail-fast on parse errors with clear error messages
    ABOUTME: Expands environment variables in all string values
    ABOUTME: Supports both stdio and HTTP server types

    Args:
        path: Path to config.json file

    Returns:
        Parsed Config object

    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If JSON syntax is invalid
        ValueError: If required fields are missing or invalid
    """
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Validate required top-level structure
    if "mcpx" not in data:
        raise ValueError("Missing required 'mcpx' section in config")

    mcpx_section = data["mcpx"]
    if "version" not in mcpx_section:
        raise ValueError("Missing required 'version' field in 'mcpx' section")

    if "servers" not in data:
        raise ValueError("Missing required 'servers' section in config")

    version = mcpx_section["version"]
    servers_data = data["servers"]

    # Parse each server definition
    servers: dict[str, MCPServer] = {}
    for server_name, server_config in servers_data.items():
        # Validate required type field
        if "type" not in server_config:
            raise ValueError(
                f"Server '{server_name}' missing required 'type' field"
            )

        server_type = server_config["type"]

        if server_type == "stdio":
            # Validate stdio-specific required fields
            if "command" not in server_config:
                raise ValueError(
                    f"Server '{server_name}' missing required 'command' field for stdio type"
                )

            command = server_config["command"]
            args = server_config.get("args", [])
            env_dict = server_config.get("env", {})

            # Expand environment variables in all string values
            command = expand_env_vars(command)
            args = [expand_env_vars(str(arg)) for arg in args]
            env = {key: expand_env_vars(str(value)) for key, value in env_dict.items()}

            servers[server_name] = MCPServer(
                name=server_name,
                type="stdio",
                command=command,
                args=args,
                env=env,
            )

        elif server_type == "http":
            # Validate HTTP-specific required fields
            if "url" not in server_config:
                raise ValueError(
                    f"Server '{server_name}' missing required 'url' field for http type"
                )

            url = server_config["url"]
            headers = server_config.get("headers", {})

            # Expand environment variables
            url = expand_env_vars(url)
            headers = {
                key: expand_env_vars(str(value))
                for key, value in headers.items()
            }

            servers[server_name] = MCPServer(
                name=server_name,
                type="http",
                url=url,
                headers=headers,
            )

        else:
            raise ValueError(
                f"Server '{server_name}' has invalid type '{server_type}'. Must be 'stdio' or 'http'."
            )

    return Config(version=version, servers=servers)
