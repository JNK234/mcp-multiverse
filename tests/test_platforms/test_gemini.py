# Tests for Gemini CLI platform adapter
from pathlib import Path

from mcpx.models import MCPServer
from mcpx.platforms.gemini import GeminiAdapter


def test_gemini_adapter_properties(tmp_path: Path) -> None:
    """Test adapter name and config_path property."""
    config_file = tmp_path / "settings.json"
    adapter = GeminiAdapter(config_path=config_file)

    assert adapter.name == "Gemini CLI"
    assert adapter.config_path is None  # File doesn't exist yet


def test_gemini_load_empty(tmp_path: Path) -> None:
    """Test loading when config doesn't exist."""
    config_file = tmp_path / "settings.json"
    adapter = GeminiAdapter(config_path=config_file)

    servers = adapter.load()
    assert servers == {}


def test_gemini_load_servers(tmp_path: Path) -> None:
    """Test loading existing servers from config."""
    config_file = tmp_path / "settings.json"
    config_file.write_text(
        """{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/projects"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "ghp_xxxx"
      }
    }
  },
  "selectedAuthType": "google",
  "theme": "dark"
}"""
    )

    adapter = GeminiAdapter(config_path=config_file)
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


def test_gemini_save_creates_file(tmp_path: Path) -> None:
    """Test saving creates config file if missing."""
    config_file = tmp_path / "settings.json"
    adapter = GeminiAdapter(config_path=config_file)

    servers = {
        "filesystem": MCPServer(
            name="filesystem",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/projects"],
        ),
    }

    adapter.save(servers)

    assert config_file.exists()
    content = config_file.read_text()
    assert '"mcpServers"' in content
    assert '"command": "npx"' in content


def test_gemini_save_preserves_other_settings(tmp_path: Path) -> None:
    """Test saving preserves non-MCP settings like selectedAuthType and theme."""
    config_file = tmp_path / "settings.json"
    config_file.write_text(
        """{
  "mcpServers": {
    "old-server": {
      "command": "old-command"
    }
  },
  "selectedAuthType": "google",
  "theme": "dark",
  "customSetting": "value"
}"""
    )

    adapter = GeminiAdapter(config_path=config_file)

    servers = {
        "filesystem": MCPServer(
            name="filesystem",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem"],
        ),
    }

    adapter.save(servers)

    # Verify both new MCP servers and old settings exist
    content = config_file.read_text()
    assert '"mcpServers"' in content
    assert '"filesystem"' in content
    assert '"selectedAuthType": "google"' in content
    assert '"theme": "dark"' in content
    assert '"customSetting": "value"' in content

    # Verify old server is replaced
    assert '"old-server"' not in content


def test_gemini_save_replaces_all(tmp_path: Path) -> None:
    """Test saving replaces all MCP servers (orphan preservation is sync-level concern)."""
    config_file = tmp_path / "settings.json"
    config_file.write_text(
        """{
  "mcpServers": {
    "orphan": {
      "command": "custom-command",
      "args": ["--orphan"]
    }
  },
  "selectedAuthType": "google"
}"""
    )

    adapter = GeminiAdapter(config_path=config_file)

    # Save only managed servers - orphans are replaced
    servers = {
        "filesystem": MCPServer(
            name="filesystem",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem"],
        ),
    }

    adapter.save(servers)

    # Verify only managed servers exist (orphans replaced)
    content = config_file.read_text()
    assert '"filesystem"' in content
    assert '"orphan"' not in content
    assert '"command": "npx"' in content
    assert '"selectedAuthType": "google"' in content  # Non-MCP setting preserved


def test_gemini_save_updates_existing(tmp_path: Path) -> None:
    """Test saving updates existing servers."""
    config_file = tmp_path / "settings.json"
    config_file.write_text(
        """{
  "mcpServers": {
    "filesystem": {
      "command": "old-command",
      "args": ["--old"]
    }
  },
  "selectedAuthType": "google"
}"""
    )

    adapter = GeminiAdapter(config_path=config_file)

    servers = {
        "filesystem": MCPServer(
            name="filesystem",
            command="new-command",
            args=["--new"],
        ),
    }

    adapter.save(servers)

    content = config_file.read_text()
    assert '"command": "new-command"' in content
    assert '"args":' in content  # Just check key exists, not exact formatting
    assert '--new' in content
    assert '"command": "old-command"' not in content
    assert '"selectedAuthType": "google"' in content  # Preserved


def test_gemini_roundtrip(tmp_path: Path) -> None:
    """Test loading and saving preserves data correctly."""
    config_file = tmp_path / "settings.json"
    adapter = GeminiAdapter(config_path=config_file)

    original_servers = {
        "filesystem": MCPServer(
            name="filesystem",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/projects"],
            env={"DEBUG": "1"},
        ),
        "github": MCPServer(
            name="github",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_TOKEN": "ghp_xxxx"},
        ),
    }

    # Set up initial config with other settings
    config_file.write_text(
        """{
  "selectedAuthType": "google",
  "theme": "dark"
}"""
    )

    # Save
    adapter.save(original_servers)

    # Load
    loaded_servers = adapter.load()

    # Verify
    assert len(loaded_servers) == 2
    for name, server in loaded_servers.items():
        original = original_servers[name]
        assert server.name == original.name
        assert server.command == original.command
        assert server.args == original.args
        assert server.env == original.env

    # Verify other settings preserved
    content = config_file.read_text()
    assert '"selectedAuthType": "google"' in content
    assert '"theme": "dark"' in content


def test_gemini_adapter_protocol_compliance(tmp_path: Path) -> None:
    """Test GeminiAdapter implements PlatformAdapter protocol correctly."""
    from mcpx.models import PlatformAdapter

    config_file = tmp_path / "settings.json"
    adapter = GeminiAdapter(config_path=config_file)

    # Verify it's a PlatformAdapter
    assert isinstance(adapter, PlatformAdapter)

    # Verify required properties and methods exist
    assert hasattr(adapter, "name")
    assert hasattr(adapter, "config_path")
    assert hasattr(adapter, "load")
    assert hasattr(adapter, "save")

    # Verify they're callable
    assert callable(adapter.load)
    assert callable(adapter.save)


def test_gemini_default_path() -> None:
    """Test default config path is ~/.gemini/settings.json."""
    adapter = GeminiAdapter()

    assert adapter._config_path == Path.home() / ".gemini" / "settings.json"


def test_gemini_custom_path(tmp_path: Path) -> None:
    """Test custom config path."""
    custom_path = tmp_path / "custom" / "settings.json"
    adapter = GeminiAdapter(config_path=custom_path)

    assert adapter._config_path == custom_path


def test_gemini_json_format(tmp_path: Path) -> None:
    """Test JSON output format matches spec (2-space indent, sorted keys)."""
    config_file = tmp_path / "settings.json"
    adapter = GeminiAdapter(config_path=config_file)

    # Set up initial config with other settings
    config_file.write_text('{"selectedAuthType": "google"}')

    servers = {
        "github": MCPServer(
            name="github",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_TOKEN": "ghp_xxxx"},
        ),
    }

    adapter.save(servers)

    content = config_file.read_text()

    # Verify format
    assert '  "args":' in content  # 2-space indent
    assert '  "command":' in content
    assert '  "env":' in content
    assert '  "selectedAuthType":' in content  # Other setting preserved

    # Verify trailing newline
    assert content.endswith("\n")


def test_gemini_empty_env_not_written(tmp_path: Path) -> None:
    """Test that empty env dict is not written to output."""
    config_file = tmp_path / "settings.json"
    adapter = GeminiAdapter(config_path=config_file)

    servers = {
        "filesystem": MCPServer(
            name="filesystem",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem"],
            env={},  # Empty env
        ),
    }

    adapter.save(servers)

    content = config_file.read_text()
    # Env should not be in output when empty
    lines = content.split("\n")
    for line in lines:
        if '"env"' in line and "filesystem" in "\n".join(lines):
            # Check if it's actually empty (not from other settings)
            # Find the server block
            in_server_block = False
            for line_item in lines:
                if '"filesystem"' in line_item:
                    in_server_block = True
                if in_server_block and "}" in line_item and "env" not in line_item:
                    in_server_block = False
                if in_server_block and '"env"' in line_item:
                    raise AssertionError("Empty env dict should not be written")
