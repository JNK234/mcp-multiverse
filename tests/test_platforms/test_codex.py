# Tests for Codex CLI platform adapter
from pathlib import Path

import pytest

from mcpx.models import MCPServer
from mcpx.platforms.codex import CodexAdapter


def test_codex_adapter_properties(tmp_path: Path) -> None:
    """Test adapter name and config_path property."""
    config_file = tmp_path / "config.toml"
    adapter = CodexAdapter(config_path=config_file)

    assert adapter.name == "Codex CLI"
    assert adapter.config_path is None  # File doesn't exist yet


def test_codex_load_empty(tmp_path: Path) -> None:
    """Test loading when config doesn't exist."""
    config_file = tmp_path / "config.toml"
    adapter = CodexAdapter(config_path=config_file)

    servers = adapter.load()
    assert servers == {}


def test_codex_load_servers(tmp_path: Path) -> None:
    """Test loading existing servers from config."""
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """[mcp_servers.filesystem]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/projects"]

[mcp_servers.github]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { GITHUB_TOKEN = "ghp_xxxx" }
"""
    )

    adapter = CodexAdapter(config_path=config_file)
    servers = adapter.load()

    assert len(servers) == 2
    assert "filesystem" in servers
    assert "github" in servers

    fs_server = servers["filesystem"]
    assert fs_server.name == "filesystem"
    assert fs_server.command == "npx"
    assert fs_server.args == ["-y", "@modelcontextprotocol/server-filesystem", "/projects"]
    assert fs_server.env == {}

    gh_server = servers["github"]
    assert gh_server.name == "github"
    assert gh_server.command == "npx"
    assert gh_server.args == ["-y", "@modelcontextprotocol/server-github"]
    assert gh_server.env == {"GITHUB_TOKEN": "ghp_xxxx"}


def test_codex_load_invalid_toml(tmp_path: Path) -> None:
    """Test loading invalid TOML raises ValueError."""
    config_file = tmp_path / "config.toml"
    config_file.write_text("invalid [toml")

    adapter = CodexAdapter(config_path=config_file)

    with pytest.raises(ValueError, match="Invalid TOML"):
        adapter.load()


def test_codex_save_creates_file(tmp_path: Path) -> None:
    """Test saving creates config file if missing."""
    config_file = tmp_path / "config.toml"
    adapter = CodexAdapter(config_path=config_file)

    servers = {
        "filesystem": MCPServer(
            name="filesystem",
            type="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/projects"],
        ),
    }

    adapter.save(servers)

    assert config_file.exists()
    content = config_file.read_text()
    assert "[mcp_servers.filesystem]" in content
    assert 'command = "npx"' in content


def test_codex_save_toml_format(tmp_path: Path) -> None:
    """Test TOML output format matches Codex specification."""
    config_file = tmp_path / "config.toml"
    adapter = CodexAdapter(config_path=config_file)

    servers = {
        "filesystem": MCPServer(
            name="filesystem",
            type="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/Users/user/projects"],
        ),
        "github": MCPServer(
            name="github",
            type="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxxx"},
        ),
    }

    adapter.save(servers)

    content = config_file.read_text()

    # Check section headers use mcp_servers (snake_case)
    assert "[mcp_servers.filesystem]" in content
    assert "[mcp_servers.github]" in content

    # Check command formatting
    assert 'command = "npx"' in content

    # Check args array formatting
    expected_args = (
        'args = ["-y", "@modelcontextprotocol/server-filesystem", '
        '"/Users/user/projects"]'
    )
    assert expected_args in content

    # Check env inline table formatting
    assert 'env = { GITHUB_PERSONAL_ACCESS_TOKEN = "ghp_xxxx" }' in content


def test_codex_save_with_env(tmp_path: Path) -> None:
    """Test saving server with environment variables."""
    config_file = tmp_path / "config.toml"
    adapter = CodexAdapter(config_path=config_file)

    servers = {
        "github": MCPServer(
            name="github",
            type="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_TOKEN": "ghp_test"},
        ),
    }

    adapter.save(servers)

    content = config_file.read_text()
    assert 'env = { GITHUB_TOKEN = "ghp_test" }' in content


def test_codex_save_without_env(tmp_path: Path) -> None:
    """Test saving server without environment variables."""
    config_file = tmp_path / "config.toml"
    adapter = CodexAdapter(config_path=config_file)

    servers = {
        "filesystem": MCPServer(
            name="filesystem",
            type="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem"],
        ),
    }

    adapter.save(servers)

    content = config_file.read_text()
    # Should not have env line when no env vars
    assert "env = " not in content


def test_codex_roundtrip(tmp_path: Path) -> None:
    """Test loading and saving preserves data correctly."""
    config_file = tmp_path / "config.toml"
    adapter = CodexAdapter(config_path=config_file)

    # Original servers
    original_servers = {
        "filesystem": MCPServer(
            name="filesystem",
            type="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/projects"],
            env={"PATH": "/usr/bin"},
        ),
        "github": MCPServer(
            name="github",
            type="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_TOKEN": "ghp_xxxx"},
        ),
    }

    # Save and load
    adapter.save(original_servers)
    loaded_servers = adapter.load()

    # Verify all servers preserved
    assert len(loaded_servers) == 2
    assert "filesystem" in loaded_servers
    assert "github" in loaded_servers

    # Verify filesystem server
    fs = loaded_servers["filesystem"]
    assert fs.name == "filesystem"
    assert fs.command == "npx"
    assert fs.args == ["-y", "@modelcontextprotocol/server-filesystem", "/projects"]
    assert fs.env == {"PATH": "/usr/bin"}

    # Verify github server
    gh = loaded_servers["github"]
    assert gh.name == "github"
    assert gh.command == "npx"
    assert gh.args == ["-y", "@modelcontextprotocol/server-github"]
    assert gh.env == {"GITHUB_TOKEN": "ghp_xxxx"}


def test_codex_save_special_characters(tmp_path: Path) -> None:
    """Test handling special characters in values."""
    config_file = tmp_path / "config.toml"
    adapter = CodexAdapter(config_path=config_file)

    servers = {
        "test": MCPServer(
            name="test",
            type="stdio",
            command='cmd "with" quotes',
            args=["-y", "path\\with\\backslashes"],
            env={"KEY": 'value "with" quotes'},
        ),
    }

    adapter.save(servers)

    content = config_file.read_text()
    # Verify escaping
    assert 'command = "cmd \\"with\\" quotes"' in content
    assert 'args = ["-y", "path\\\\with\\\\backslashes"]' in content
    assert 'env = { KEY = "value \\"with\\" quotes" }' in content


def test_codex_empty_args(tmp_path: Path) -> None:
    """Test saving server with empty args list."""
    config_file = tmp_path / "config.toml"
    adapter = CodexAdapter(config_path=config_file)

    servers = {
        "simple": MCPServer(
            name="simple",
            type="stdio",
            command="node",
            args=[],
        ),
    }

    adapter.save(servers)

    content = config_file.read_text()
    # Should not include args line when empty
    assert "args = " not in content
    assert 'command = "node"' in content


def test_codex_default_path(tmp_path: Path) -> None:
    """Test adapter uses default path when none provided."""
    adapter = CodexAdapter()

    assert adapter.name == "Codex CLI"
    # Should point to ~/.codex/config.toml
    assert str(adapter._config_path).endswith(".codex/config.toml")
