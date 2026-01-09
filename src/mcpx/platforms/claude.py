# Claude Code platform adapter
from pathlib import Path

from mcpx.models import MCPServer, PlatformAdapter
from mcpx.platforms.base import dict_to_server, read_json_file, server_to_dict, write_json_file


class ClaudeAdapter(PlatformAdapter):
    """Adapter for Claude Code (~/.claude.json).

    ABOUTME: Implements PlatformAdapter protocol for Claude Code
    ABOUTME: Creates config file if missing
    """

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize adapter with optional custom config path.

        ABOUTME: Defaults to ~/.claude.json if not provided
        """
        self._config_path = config_path if config_path else Path.home() / ".claude.json"

    @property
    def name(self) -> str:
        """Human-readable platform name."""
        return "Claude Code"

    @property
    def config_path(self) -> Path | None:
        """Path to platform config file."""
        return self._config_path if self._config_path.exists() else None

    def load(self) -> dict[str, MCPServer]:
        """Load existing MCP servers from platform config.

        ABOUTME: Returns empty dict if config doesn't exist
        ABOUTME: Parses 'mcpServers' key from JSON
        """
        if not self._config_path.exists():
            return {}

        data = read_json_file(self._config_path)
        mcp_servers = data.get("mcpServers", {})

        return {
            name: dict_to_server(name, server_data)
            for name, server_data in mcp_servers.items()
        }

    def save(self, servers: dict[str, MCPServer]) -> None:
        """Save MCP servers to platform config.

        ABOUTME: Creates file if missing
        ABOUTME: Uses 'mcpServers' key in JSON
        """
        # Read existing config to preserve any non-MCP settings
        existing_data = read_json_file(self._config_path) if self._config_path.exists() else {}

        # Update mcpServers section
        existing_data["mcpServers"] = {
            name: server_to_dict(server) for name, server in servers.items()
        }

        # Write updated config
        write_json_file(self._config_path, existing_data)

    def save_project(self, servers: dict[str, MCPServer], project_dir: Path) -> None:
        """Save MCP servers to project-level config.

        ABOUTME: Creates .mcp.json file in project directory
        ABOUTME: Uses mcpServers wrapper key per spec

        Args:
            servers: Dict of servers to save
            project_dir: Path to project directory
        """
        # Project-level config file
        project_config = project_dir / ".mcp.json"

        # Convert servers to dict format
        mcp_servers = {
            name: server_to_dict(server) for name, server in servers.items()
        }

        # Write project config with mcpServers wrapper
        write_json_file(project_config, {"mcpServers": mcp_servers})
