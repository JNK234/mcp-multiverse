#!/usr/bin/env python3
"""
ABOUTME: Universal MCP Server Sync Manager
ABOUTME: Synchronizes MCP server configurations across multiple platforms (Claude Code, Gemini CLI, Cline, Roo Code)
"""

import json
import argparse
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
import shutil
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/mcp-sync-manager.log')
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class MCPServer:
    """Standardized MCP server configuration"""
    command: str
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    disabled: Optional[bool] = None
    auto_approve: Optional[List[str]] = None  # Renamed from autoApprove
    timeout: Optional[int] = None
    transport_type: Optional[str] = None  # Renamed from transportType

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {"command": self.command}
        if self.args:
            result["args"] = self.args
        if self.env:
            result["env"] = self.env
        if self.disabled is not None:
            result["disabled"] = self.disabled
        if self.auto_approve is not None:
            result["autoApprove"] = self.auto_approve
        if self.timeout is not None:
            result["timeout"] = self.timeout
        if self.transport_type is not None:
            result["transportType"] = self.transport_type
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPServer":
        """Create MCPServer from dictionary"""
        return cls(
            command=data["command"],
            args=data.get("args"),
            env=data.get("env"),
            disabled=data.get("disabled"),
            auto_approve=data.get("autoApprove") or data.get("auto_approve"),
            timeout=data.get("timeout"),
            transport_type=data.get("transportType") or data.get("transport_type")
        )


class Platforms:
    """Supported MCP platform configurations"""

    def __init__(self):
        self.home = Path.home()

        # Claude Code configurations
        self.claude_user_config = self.home / ".claude" / "claude_desktop_config.json"
        self.claude_project_config = Path.cwd() / ".claude" / "mcp_config.json"

        # Claude Code compatibility: also support direct mcp.json
        self.claude_mcp_json = Path.cwd() / ".mcp.json"

        # Gemini CLI configuration
        self.gemini_config = self.home / ".gemini" / "settings.json"

        # Cline configuration
        self.cline_config = self.home / "Library" / "Application Support" / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"

        # Fallback for different OS paths
        if not self.cline_config.exists():
            # Check VS Code Insiders
            self.cline_config = self.home / "Library" / "Application Support" / "Code - Insiders" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"

        if not self.cline_config.exists():
            # Linux path
            self.cline_config = self.home / ".config" / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"

        # Windows path
        if not self.cline_config.exists():
            self.cline_config = Path(os.environ.get("APPDATA", "")) / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"

        # Roo Code configuration
        self.roo_config = self.home / "Library" / "Application Support" / "Code" / "User" / "globalStorage" / "rooveterinaryinc.roo-cline" / "settings" / "cline_mcp_settings.json"

        if not self.roo_config.exists():
            # Try different possible paths
            possible_paths = [
                self.home / "Library" / "Application Support" / "Code" / "User" / "globalStorage" / "rooveterinaryinc.roo-cline" / "settings" / "cline_mcp_settings.json",
                self.home / ".config" / "Code" / "User" / "globalStorage" / "rooveterinaryinc.roo-cline" / "settings" / "cline_mcp_settings.json",
                Path(os.environ.get("APPDATA", "")) / "Code" / "User" / "globalStorage" / "rooveterinaryinc.roo-cline" / "settings" / "cline_mcp_settings.json",
                Path.cwd() / ".roo" / "mcp.json"
            ]
            for path in possible_paths:
                if path.exists():
                    self.roo_config = path
                    break


class MCPSyncManager:
    """Main MCP sync manager class"""

    def __init__(self):
        self.platforms = Platforms()
        self.backup_dir = Path.home() / ".mcp-sync-backups"
        self.backup_dir.mkdir(exist_ok=True)

    def backup_config(self, config_path: Path, platform: str) -> Path:
        """Create a backup of configuration file"""
        if not config_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{platform}_{config_path.name}_{timestamp}.backup"
        shutil.copy2(config_path, backup_path)
        logger.info(f"Backed up {config_path} to {backup_path}")
        return backup_path

    def load_json(self, path: Path) -> Optional[Dict[str, Any]]:
        """Load JSON file with error handling"""
        try:
            if not path.exists():
                logger.warning(f"Config file not found: {path}")
                return None

            with open(path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON in {path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error reading {path}: {e}")
            return None

    def save_json(self, path: Path, data: Dict[str, Any]) -> bool:
        """Save JSON file with error handling"""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved configuration to {path}")
            return True
        except Exception as e:
            logger.error(f"Error saving {path}: {e}")
            return False

    def extract_mcp_servers(self, config: Dict[str, Any]) -> Dict[str, MCPServer]:
        """Extract MCP servers from configuration"""
        if not config or "mcpServers" not in config:
            return {}

        servers = {}
        for name, server_data in config["mcpServers"].items():
            try:
                servers[name] = MCPServer.from_dict(server_data)
            except Exception as e:
                logger.warning(f"Error parsing server {name}: {e}")

        return servers

    def merge_servers(self, existing_servers: Dict[str, MCPServer],
                     new_servers: Dict[str, MCPServer]) -> Dict[str, MCPServer]:
        """Merge server configurations, preferring new values"""
        merged = existing_servers.copy()
        for name, server in new_servers.items():
            merged[name] = server
        return merged

    def format_for_platform(self, servers: Dict[str, MCPServer],
                           platform: str) -> Dict[str, Any]:
        """Format servers for specific platform"""
        formatted_servers = {name: server.to_dict() for name, server in servers.items()}

        if platform == "claude":
            # Claude uses simple format
            return {"mcpServers": formatted_servers}

        elif platform == "gemini":
            # Gemini has additional top-level sections
            return {
                "mcpServers": formatted_servers,
                "general": {},
                "security": {},
                "ui": {},
                "output": {}
            }

        elif platform in ["cline", "roo"]:
            # Cline and Roo use camelCase and have additional metadata
            for name, server in formatted_servers.items():
                # Ensure required fields for Cline/Roo
                if "disabled" not in server:
                    server["disabled"] = False
                if "autoApprove" not in server:
                    server["autoApprove"] = []
                if "timeout" not in server:
                    server["timeout"] = 60
                if "transportType" not in server:
                    server["transportType"] = "stdio"

            return {"mcpServers": formatted_servers}

        else:
            return {"mcpServers": formatted_servers}

    def read_servers_from_all_platforms(self) -> Dict[str, MCPServer]:
        """Read and aggregate servers from all platforms"""
        all_servers = {}

        # Claude
        claude_config = self.load_json(self.platforms.claude_user_config)
        if claude_config:
            servers = self.extract_mcp_servers(claude_config)
            logger.info(f"Found {len(servers)} servers in Claude config")
            all_servers.update(servers)

        # Gemini
        gemini_config = self.load_json(self.platforms.gemini_config)
        if gemini_config:
            servers = self.extract_mcp_servers(gemini_config)
            logger.info(f"Found {len(servers)} servers in Gemini config")
            all_servers.update(servers)

        # Cline
        cline_config = self.load_json(self.platforms.cline_config)
        if cline_config:
            servers = self.extract_mcp_servers(cline_config)
            logger.info(f"Found {len(servers)} servers in Cline config")
            all_servers.update(servers)

        # Roo
        roo_config = self.load_json(self.platforms.roo_config)
        if roo_config:
            servers = self.extract_mcp_servers(roo_config)
            logger.info(f"Found {len(servers)} servers in Roo config")
            all_servers.update(servers)

        logger.info(f"Total unique servers found across all platforms: {len(all_servers)}")
        return all_servers

    def sync_to_platform(self, servers: Dict[str, MCPServer], platform: str) -> bool:
        """Sync servers to a specific platform"""
        if platform == "claude":
            config_path = self.platforms.claude_user_config
        elif platform == "gemini":
            config_path = self.platforms.gemini_config
        elif platform == "cline":
            config_path = self.platforms.cline_config
        elif platform == "roo":
            config_path = self.platforms.roo_config
        else:
            logger.error(f"Unknown platform: {platform}")
            return False

        # Create backup
        self.backup_config(config_path, platform)

        # Load existing config if it exists
        existing_config = self.load_json(config_path) or {}

        # Format servers for the platform
        formatted_config = self.format_for_platform(servers, platform)

        # Merge non-MCP sections for platforms that have them
        if platform == "gemini":
            # Preserve existing general/security/ui/output sections
            for section in ["general", "security", "ui", "output"]:
                if section in existing_config:
                    formatted_config[section] = existing_config[section]

        # Save the updated config
        return self.save_json(config_path, formatted_config)

    def sync_all(self, source_platform: str = None) -> Dict[str, bool]:
        """Sync MCP servers to all platforms"""
        results = {}

        # Get servers to sync
        if source_platform:
            # Sync from a specific platform
            if source_platform == "claude":
                config = self.load_json(self.platforms.claude_user_config)
            elif source_platform == "gemini":
                config = self.load_json(self.platforms.gemini_config)
            elif source_platform == "cline":
                config = self.load_json(self.platforms.cline_config)
            elif source_platform == "roo":
                config = self.load_json(self.platforms.roo_config)
            else:
                logger.error(f"Unknown source platform: {source_platform}")
                return results

            servers = self.extract_mcp_servers(config or {})
            logger.info(f"Syncing from {source_platform}: {len(servers)} servers")
        else:
            # Sync aggregated servers from all platforms
            servers = self.read_servers_from_all_platforms()

        # Sync to all platforms
        platforms = ["claude", "gemini", "cline", "roo"]
        for platform in platforms:
            logger.info(f"\nSyncing to {platform}...")
            try:
                success = self.sync_to_platform(servers, platform)
                results[platform] = success
                if success:
                    logger.info(f"✓ Successfully synced to {platform}")
                else:
                    logger.error(f"✗ Failed to sync to {platform}")
            except Exception as e:
                logger.error(f"✗ Error syncing to {platform}: {e}")
                results[platform] = False

        return results

    def list_servers(self) -> None:
        """List all MCP servers across platforms"""
        servers = self.read_servers_from_all_platforms()

        if not servers:
            logger.info("No MCP servers found")
            return

        print("\n=== MCP Servers Across All Platforms ===\n")

        for name, server in sorted(servers.items()):
            print(f"\n🔧 {name}")
            print(f"   Command: {server.command}")
            if server.args:
                print(f"   Args: {' '.join(server.args)}")
            if server.env:
                print(f"   Environment variables: {', '.join(server.env.keys())}")
            if server.disabled is not None:
                print(f"   Status: {'Disabled' if server.disabled else 'Enabled'}")

        print(f"\nTotal: {len(servers)} servers\n")

    def add_server(self, name: str, command: str, args: List[str] = None,
                   env: Dict[str, str] = None) -> bool:
        """Add a new MCP server to all platforms"""
        server = MCPServer(command=command, args=args, env=env)

        # Get existing servers from all platforms
        servers = self.read_servers_from_all_platforms()

        # Add or update the server
        servers[name] = server

        # Sync to all platforms
        results = self.sync_all()

        success = all(results.values())
        if success:
            logger.info(f"Successfully added server '{name}' to all platforms")
        else:
            logger.error(f"Failed to add server '{name}'. Results: {results}")

        return success

    def remove_server(self, name: str) -> bool:
        """Remove an MCP server from all platforms"""
        # Get existing servers from all platforms
        servers = self.read_servers_from_all_platforms()

        if name not in servers:
            logger.error(f"Server '{name}' not found")
            return False

        # Remove the server
        del servers[name]

        # Sync to all platforms
        results = self.sync_all()

        success = all(results.values())
        if success:
            logger.info(f"Successfully removed server '{name}' from all platforms")
        else:
            logger.error(f"Failed to remove server '{name}'. Results: {results}")

        return success


def main():
    parser = argparse.ArgumentParser(
        description="Universal MCP Server Sync Manager - Sync MCP configurations across platforms"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Sync MCP servers across platforms")
    sync_parser.add_argument(
        "--from",
        dest="source_platform",
        choices=["claude", "gemini", "cline", "roo"],
        help="Sync from a specific platform (default: merge from all)"
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List all MCP servers")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add an MCP server")
    add_parser.add_argument("name", help="Server name")
    add_parser.add_argument("command", help="Command to execute")
    add_parser.add_argument("--args", nargs="*", help="Command arguments")
    add_parser.add_argument("--env", nargs="*", help="Environment variables (KEY=VALUE)")

    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove an MCP server")
    remove_parser.add_argument("name", help="Server name")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = MCPSyncManager()

    if args.command == "sync":
        results = manager.sync_all(getattr(args, "source_platform", None))

        print("\n=== Sync Results ===")
        for platform, success in results.items():
            status = "✓" if success else "✗"
            print(f"{status} {platform}")

        if all(results.values()):
            print("\nAll platforms synced successfully!")
            sys.exit(0)
        else:
            print("\nSome platforms failed to sync. Check logs for details.")
            sys.exit(1)

    elif args.command == "list":
        manager.list_servers()

    elif args.command == "add":
        env_dict = {}
        if args.env:
            for env_var in args.env:
                if "=" in env_var:
                    key, value = env_var.split("=", 1)
                    env_dict[key] = value

        success = manager.add_server(args.name, args.command, args.args, env_dict)
        sys.exit(0 if success else 1)

    elif args.command == "remove":
        success = manager.remove_server(args.name)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
