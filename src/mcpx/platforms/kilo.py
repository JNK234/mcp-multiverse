# Kilo Code platform adapter
import os
import sys
from pathlib import Path

from mcpx.models import MCPServer, PlatformAdapter
from mcpx.platforms.base import dict_to_server, read_json_file, server_to_dict, write_json_file


class KiloAdapter(PlatformAdapter):
    """Adapter for Kilo Code VS Code extension (kilocode.kilocode).

    ABOUTME: Implements PlatformAdapter protocol for Kilo Code
    ABOUTME: Uses mcp_settings.json in globalStorage (different filename!)
    """

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize adapter with optional custom config path.

        ABOUTME: Auto-detects path based on OS if not provided
        ABOUTME: Checks both Code/ and Code - Insiders/ directories
        """
        if config_path:
            self._config_path = config_path
        else:
            self._config_path = self._get_default_path()

    def _get_default_path(self) -> Path:
        """Get default config path based on platform.

        ABOUTME: Uses VS Code globalStorage directory
        ABOUTME: Checks Code/ and Code - Insiders/ for existing configs
        """
        base_path = self._get_base_path()
        extension_id = "kilocode.kilocode"
        filename = "mcp_settings.json"  # Different from Cline/Roo!

        # Check both Code and Code - Insiders
        for variant in ["Code", "Code - Insiders"]:
            path = base_path / variant / "User/globalStorage" / extension_id / "settings" / filename
            if path.exists():
                return path

        # Default to Code if none exist
        return base_path / "Code" / "User/globalStorage" / extension_id / "settings" / filename

    def _get_base_path(self) -> Path:
        """Get base VS Code path for current OS.

        ABOUTME: Returns platform-specific globalStorage location
        """
        if sys.platform == "darwin":
            return Path.home() / "Library/Application Support"
        elif sys.platform == "win32":
            return Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
        else:  # Linux and others
            return Path.home() / ".config"

    @property
    def name(self) -> str:
        """Human-readable platform name."""
        return "Kilo Code"

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
        ABOUTME: Adds required VS Code defaults: disabled, alwaysAllow
        """
        # Read existing config to preserve any non-MCP settings
        existing_data = read_json_file(self._config_path) if self._config_path.exists() else {}

        # Update mcpServers section with required VS Code defaults
        existing_data["mcpServers"] = {
            name: {
                **server_to_dict(server),
                "disabled": False,
                "alwaysAllow": [],
            }
            for name, server in servers.items()
        }

        # Write updated config
        write_json_file(self._config_path, existing_data)

    def save_project(self, servers: dict[str, MCPServer], project_dir: Path) -> None:
        """Save MCP servers to project-level config.

        ABOUTME: Creates .kilocode/mcp.json file in project directory
        ABOUTME: Uses mcpServers wrapper key per spec

        Args:
            servers: Dict of servers to save
            project_dir: Path to project directory
        """
        # Project-level config directory and file
        kilo_dir = project_dir / ".kilocode"
        project_config = kilo_dir / "mcp.json"

        # Create .kilocode directory if it doesn't exist
        kilo_dir.mkdir(exist_ok=True)

        # Convert servers to dict format with required VS Code defaults
        mcp_servers = {
            name: {
                **server_to_dict(server),
                "disabled": False,
                "alwaysAllow": [],
            }
            for name, server in servers.items()
        }

        # Write project config with mcpServers wrapper
        write_json_file(project_config, {"mcpServers": mcp_servers})
