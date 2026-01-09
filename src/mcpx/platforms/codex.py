# Codex CLI platform adapter
from pathlib import Path
from typing import Any

import tomli

from mcpx.models import MCPServer, PlatformAdapter
from mcpx.platforms.base import dict_to_server
from mcpx.utils.toml_writer import write_toml_simple


class CodexAdapter(PlatformAdapter):
    """Adapter for Codex CLI (~/.codex/config.toml).

    ABOUTME: Implements PlatformAdapter protocol for Codex CLI
    ABOUTME: Uses snake_case mcp_servers key (not mcpServers)
    """

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize adapter with optional custom config path.

        ABOUTME: Defaults to ~/.codex/config.toml if not provided
        """
        self._config_path = config_path if config_path else Path.home() / ".codex" / "config.toml"

    @property
    def name(self) -> str:
        """Human-readable platform name."""
        return "Codex CLI"

    @property
    def config_path(self) -> Path | None:
        """Path to platform config file."""
        return self._config_path if self._config_path.exists() else None

    def load(self) -> dict[str, MCPServer]:
        """Load existing MCP servers from platform config.

        ABOUTME: Returns empty dict if config doesn't exist
        ABOUTME: Parses 'mcp_servers' key from TOML (snake_case)
        ABOUTME: Only loads stdio servers (HTTP not supported by Codex)
        """
        if not self._config_path.exists():
            return {}

        try:
            with open(self._config_path, "rb") as f:
                data = tomli.load(f)
        except tomli.TOMLDecodeError as e:
            raise ValueError(f"Invalid TOML in {self._config_path}: {e}") from e

        mcp_servers = data.get("mcp_servers", {})

        return {
            name: dict_to_server(name, server_data)
            for name, server_data in mcp_servers.items()
        }

    def save(self, servers: dict[str, MCPServer]) -> None:
        """Save MCP servers to platform config.

        ABOUTME: Creates file if missing
        ABOUTME: Uses mcp_servers key (snake_case per Codex convention)
        ABOUTME: Only saves stdio servers (HTTP not supported by Codex)
        """
        # Filter to only stdio servers
        stdio_servers = {
            name: server
            for name, server in servers.items()
            if server.type == "stdio"
        }

        # Convert servers to dict format
        mcp_servers_dict: dict[str, dict[str, Any]] = {}
        for name, server in stdio_servers.items():
            server_dict: dict[str, Any] = {
                "command": server.command,
                "args": server.args,
            }
            if server.env:
                server_dict["env"] = server.env
            mcp_servers_dict[name] = server_dict

        # Write TOML with mcp_servers key
        write_toml_simple({"mcp_servers": mcp_servers_dict}, self._config_path)

    def save_project(self, servers: dict[str, MCPServer], project_dir: Path) -> None:
        """Save MCP servers to project-level config.

        ABOUTME: Codex CLI doesn't support project-level configs
        ABOUTME: Raises NotImplementedError
        """
        raise NotImplementedError("Codex CLI doesn't support project-level MCP configs")
