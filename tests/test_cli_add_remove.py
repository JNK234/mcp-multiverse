# ABOUTME: Tests for mcpx add and remove CLI commands
# ABOUTME: Tests both interactive and non-interactive modes

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from mcpx.cli import cmd_add, cmd_remove, EXIT_SUCCESS, EXIT_CONFIG_ERROR, EXIT_PARTIAL
from mcpx.config import (
    add_server_to_config,
    load_config,
    remove_server_from_config,
    save_config,
)
from mcpx.models import Config, MCPServer


class TestSaveConfig:
    """Tests for save_config function."""

    def test_save_minimal_config(self, tmp_path: Path) -> None:
        """Test saving a minimal config."""
        config_file = tmp_path / "config.json"
        config = Config(
            version="1.0",
            servers={
                "test": MCPServer(
                    name="test",
                    type="stdio",
                    command="echo",
                )
            }
        )

        save_config(config_file, config)

        # Verify file was created
        assert config_file.exists()

        # Verify content
        data = json.loads(config_file.read_text())
        assert data["mcpx"]["version"] == "1.0"
        assert "test" in data["servers"]
        assert data["servers"]["test"]["type"] == "stdio"
        assert data["servers"]["test"]["command"] == "echo"

    def test_save_config_with_args_and_env(self, tmp_path: Path) -> None:
        """Test saving config with args and env vars."""
        config_file = tmp_path / "config.json"
        config = Config(
            version="1.0",
            servers={
                "github": MCPServer(
                    name="github",
                    type="stdio",
                    command="npx",
                    args=["-y", "@mcp/github"],
                    env={"TOKEN": "secret"},
                )
            }
        )

        save_config(config_file, config)

        data = json.loads(config_file.read_text())
        assert data["servers"]["github"]["args"] == ["-y", "@mcp/github"]
        assert data["servers"]["github"]["env"] == {"TOKEN": "secret"}

    def test_save_http_server(self, tmp_path: Path) -> None:
        """Test saving HTTP server type."""
        config_file = tmp_path / "config.json"
        config = Config(
            version="1.0",
            servers={
                "api": MCPServer(
                    name="api",
                    type="http",
                    url="https://api.example.com/mcp",
                    headers={"Authorization": "Bearer token"},
                )
            }
        )

        save_config(config_file, config)

        data = json.loads(config_file.read_text())
        assert data["servers"]["api"]["type"] == "http"
        assert data["servers"]["api"]["url"] == "https://api.example.com/mcp"
        assert data["servers"]["api"]["headers"] == {"Authorization": "Bearer token"}

    def test_save_creates_parent_directory(self, tmp_path: Path) -> None:
        """Test that save_config creates parent directories."""
        config_file = tmp_path / "nested" / "dir" / "config.json"
        config = Config(version="1.0", servers={})

        save_config(config_file, config)

        assert config_file.exists()


class TestAddServerToConfig:
    """Tests for add_server_to_config function."""

    def test_add_to_empty_config(self, tmp_path: Path) -> None:
        """Test adding server when no config exists."""
        config_file = tmp_path / "config.json"
        server = MCPServer(
            name="test",
            type="stdio",
            command="echo",
        )

        add_server_to_config(config_file, server)

        config = load_config(config_file)
        assert "test" in config.servers
        assert config.servers["test"].command == "echo"

    def test_add_to_existing_config(self, tmp_path: Path) -> None:
        """Test adding server to existing config."""
        config_file = tmp_path / "config.json"

        # Create initial config
        initial = Config(
            version="1.0",
            servers={
                "existing": MCPServer(
                    name="existing",
                    type="stdio",
                    command="npx",
                )
            }
        )
        save_config(config_file, initial)

        # Add new server
        new_server = MCPServer(
            name="new",
            type="stdio",
            command="node",
        )
        add_server_to_config(config_file, new_server)

        config = load_config(config_file)
        assert len(config.servers) == 2
        assert "existing" in config.servers
        assert "new" in config.servers

    def test_add_replaces_existing(self, tmp_path: Path) -> None:
        """Test that adding a server with existing name replaces it."""
        config_file = tmp_path / "config.json"

        # Create initial config
        initial = Config(
            version="1.0",
            servers={
                "test": MCPServer(
                    name="test",
                    type="stdio",
                    command="old-command",
                )
            }
        )
        save_config(config_file, initial)

        # Replace with new server
        new_server = MCPServer(
            name="test",
            type="stdio",
            command="new-command",
        )
        add_server_to_config(config_file, new_server)

        config = load_config(config_file)
        assert len(config.servers) == 1
        assert config.servers["test"].command == "new-command"


class TestRemoveServerFromConfig:
    """Tests for remove_server_from_config function."""

    def test_remove_existing_server(self, tmp_path: Path) -> None:
        """Test removing an existing server."""
        config_file = tmp_path / "config.json"

        # Create config with server
        initial = Config(
            version="1.0",
            servers={
                "test": MCPServer(
                    name="test",
                    type="stdio",
                    command="echo",
                )
            }
        )
        save_config(config_file, initial)

        # Remove server
        result = remove_server_from_config(config_file, "test")

        assert result is True
        config = load_config(config_file)
        assert "test" not in config.servers

    def test_remove_nonexistent_server(self, tmp_path: Path) -> None:
        """Test removing a server that doesn't exist."""
        config_file = tmp_path / "config.json"

        # Create config without the target server
        initial = Config(
            version="1.0",
            servers={
                "other": MCPServer(
                    name="other",
                    type="stdio",
                    command="echo",
                )
            }
        )
        save_config(config_file, initial)

        # Try to remove non-existent server
        result = remove_server_from_config(config_file, "test")

        assert result is False
        config = load_config(config_file)
        assert "other" in config.servers

    def test_remove_from_missing_file(self, tmp_path: Path) -> None:
        """Test removing from non-existent config file."""
        config_file = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            remove_server_from_config(config_file, "test")

    def test_remove_leaves_other_servers(self, tmp_path: Path) -> None:
        """Test that removing one server doesn't affect others."""
        config_file = tmp_path / "config.json"

        # Create config with multiple servers
        initial = Config(
            version="1.0",
            servers={
                "server1": MCPServer(
                    name="server1",
                    type="stdio",
                    command="cmd1",
                ),
                "server2": MCPServer(
                    name="server2",
                    type="stdio",
                    command="cmd2",
                ),
                "server3": MCPServer(
                    name="server3",
                    type="stdio",
                    command="cmd3",
                ),
            }
        )
        save_config(config_file, initial)

        # Remove middle server
        remove_server_from_config(config_file, "server2")

        config = load_config(config_file)
        assert len(config.servers) == 2
        assert "server1" in config.servers
        assert "server2" not in config.servers
        assert "server3" in config.servers


class TestCmdAddNonInteractive:
    """Tests for cmd_add in non-interactive mode."""

    def test_add_stdio_server(self, tmp_path: Path) -> None:
        """Test adding a stdio server non-interactively."""
        config_file = tmp_path / "config.json"

        # Create mock args
        args = MagicMock()
        args.name = "myserver"
        args.type = "stdio"
        args.command = "npx"
        args.url = None
        args.args = "-y,@mcp/package"
        args.env = "TOKEN=secret"
        args.headers = None

        # Mock the config path and sync
        with patch("mcpx.cli.get_config_path", return_value=config_file):
            with patch("mcpx.cli.sync_all") as mock_sync:
                mock_sync.return_value = MagicMock(
                    servers_synced={"Claude": 1},
                    errors=[]
                )
                result = cmd_add(args)

        assert result == EXIT_SUCCESS

        # Verify server was added
        config = load_config(config_file)
        assert "myserver" in config.servers
        server = config.servers["myserver"]
        assert server.type == "stdio"
        assert server.command == "npx"
        assert server.args == ["-y", "@mcp/package"]
        assert server.env == {"TOKEN": "secret"}

    def test_add_http_server(self, tmp_path: Path) -> None:
        """Test adding an HTTP server non-interactively."""
        config_file = tmp_path / "config.json"

        args = MagicMock()
        args.name = "api"
        args.type = "http"
        args.command = None
        args.url = "https://api.example.com/mcp"
        args.args = None
        args.env = None
        args.headers = "Authorization=Bearer token"

        with patch("mcpx.cli.get_config_path", return_value=config_file):
            with patch("mcpx.cli.sync_all") as mock_sync:
                mock_sync.return_value = MagicMock(
                    servers_synced={"Claude": 1},
                    errors=[]
                )
                result = cmd_add(args)

        assert result == EXIT_SUCCESS

        config = load_config(config_file)
        assert "api" in config.servers
        server = config.servers["api"]
        assert server.type == "http"
        assert server.url == "https://api.example.com/mcp"
        assert server.headers == {"Authorization": "Bearer token"}

    def test_add_stdio_without_command(self, tmp_path: Path) -> None:
        """Test adding stdio server without command fails."""
        config_file = tmp_path / "config.json"

        args = MagicMock()
        args.name = "myserver"
        args.type = "stdio"
        args.command = None
        args.url = None
        args.args = None
        args.env = None
        args.headers = None

        with patch("mcpx.cli.get_config_path", return_value=config_file):
            result = cmd_add(args)

        assert result == EXIT_CONFIG_ERROR

    def test_add_http_without_url(self, tmp_path: Path) -> None:
        """Test adding HTTP server without URL fails."""
        config_file = tmp_path / "config.json"

        args = MagicMock()
        args.name = "api"
        args.type = "http"
        args.command = None
        args.url = None
        args.args = None
        args.env = None
        args.headers = None

        with patch("mcpx.cli.get_config_path", return_value=config_file):
            result = cmd_add(args)

        assert result == EXIT_CONFIG_ERROR

    def test_add_with_partial_sync(self, tmp_path: Path) -> None:
        """Test add command when sync has errors."""
        config_file = tmp_path / "config.json"

        args = MagicMock()
        args.name = "test"
        args.type = "stdio"
        args.command = "echo"
        args.url = None
        args.args = None
        args.env = None
        args.headers = None

        with patch("mcpx.cli.get_config_path", return_value=config_file):
            with patch("mcpx.cli.sync_all") as mock_sync:
                mock_sync.return_value = MagicMock(
                    servers_synced={"Claude": 1, "Gemini": 0},
                    errors=["Gemini: config path not found"]
                )
                result = cmd_add(args)

        assert result == EXIT_PARTIAL


class TestCmdAddInteractive:
    """Tests for cmd_add in interactive mode."""

    def test_add_stdio_interactive(self, tmp_path: Path) -> None:
        """Test adding stdio server interactively."""
        config_file = tmp_path / "config.json"

        args = MagicMock()
        args.name = "myserver"
        args.type = None  # Triggers interactive mode

        # Mock input() calls
        inputs = [
            "stdio",      # type
            "npx",        # command
            "-y,@mcp/pkg", # args
            "TOKEN=secret", # first env var
            "",           # end env vars
        ]

        with patch("mcpx.cli.get_config_path", return_value=config_file):
            with patch("mcpx.cli.sync_all") as mock_sync:
                mock_sync.return_value = MagicMock(
                    servers_synced={"Claude": 1},
                    errors=[]
                )
                with patch("builtins.input", side_effect=inputs):
                    result = cmd_add(args)

        assert result == EXIT_SUCCESS
        config = load_config(config_file)
        assert "myserver" in config.servers

    def test_add_http_interactive(self, tmp_path: Path) -> None:
        """Test adding HTTP server interactively."""
        config_file = tmp_path / "config.json"

        args = MagicMock()
        args.name = "api"
        args.type = None

        inputs = [
            "http",                          # type
            "https://api.example.com/mcp",   # url
            "Authorization=Bearer token",    # first header
            "",                              # end headers
        ]

        with patch("mcpx.cli.get_config_path", return_value=config_file):
            with patch("mcpx.cli.sync_all") as mock_sync:
                mock_sync.return_value = MagicMock(
                    servers_synced={"Claude": 1},
                    errors=[]
                )
                with patch("builtins.input", side_effect=inputs):
                    result = cmd_add(args)

        assert result == EXIT_SUCCESS
        config = load_config(config_file)
        assert "api" in config.servers
        assert config.servers["api"].type == "http"


class TestCmdRemove:
    """Tests for cmd_remove command."""

    def test_remove_existing_server(self, tmp_path: Path) -> None:
        """Test removing an existing server."""
        config_file = tmp_path / "config.json"

        # Create initial config
        initial = Config(
            version="1.0",
            servers={
                "test": MCPServer(
                    name="test",
                    type="stdio",
                    command="echo",
                )
            }
        )
        save_config(config_file, initial)

        args = MagicMock()
        args.name = "test"

        with patch("mcpx.cli.get_config_path", return_value=config_file):
            with patch("mcpx.cli.sync_all") as mock_sync:
                mock_sync.return_value = MagicMock(
                    servers_synced={"Claude": 0},
                    errors=[]
                )
                result = cmd_remove(args)

        assert result == EXIT_SUCCESS
        config = load_config(config_file)
        assert "test" not in config.servers

    def test_remove_nonexistent_server(self, tmp_path: Path) -> None:
        """Test removing a server that doesn't exist."""
        config_file = tmp_path / "config.json"

        # Create config without target server
        initial = Config(
            version="1.0",
            servers={
                "other": MCPServer(
                    name="other",
                    type="stdio",
                    command="echo",
                )
            }
        )
        save_config(config_file, initial)

        args = MagicMock()
        args.name = "nonexistent"

        with patch("mcpx.cli.get_config_path", return_value=config_file):
            result = cmd_remove(args)

        assert result == EXIT_CONFIG_ERROR

    def test_remove_from_missing_config(self, tmp_path: Path) -> None:
        """Test removing when config file doesn't exist."""
        config_file = tmp_path / "nonexistent.json"

        args = MagicMock()
        args.name = "test"

        with patch("mcpx.cli.get_config_path", return_value=config_file):
            result = cmd_remove(args)

        assert result == EXIT_CONFIG_ERROR

    def test_remove_with_partial_sync(self, tmp_path: Path) -> None:
        """Test remove command when sync has errors."""
        config_file = tmp_path / "config.json"

        initial = Config(
            version="1.0",
            servers={
                "test": MCPServer(
                    name="test",
                    type="stdio",
                    command="echo",
                )
            }
        )
        save_config(config_file, initial)

        args = MagicMock()
        args.name = "test"

        with patch("mcpx.cli.get_config_path", return_value=config_file):
            with patch("mcpx.cli.sync_all") as mock_sync:
                mock_sync.return_value = MagicMock(
                    servers_synced={"Claude": 0, "Gemini": 0},
                    errors=["Gemini: config path not found"]
                )
                result = cmd_remove(args)

        assert result == EXIT_PARTIAL
