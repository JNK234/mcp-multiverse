# Tests for configuration loading
import tomllib

import pytest

from mcpx.config import CONFIG_FILE, ensure_config_dir, get_config_path, load_config


def test_get_config_path():
    """Test getting config file path."""
    path = get_config_path()
    assert path == CONFIG_FILE
    assert path.name == "config.toml"
    assert ".mcpx" in str(path)


def test_ensure_config_dir(tmp_path):
    """Test creating config directory."""
    # Note: This test uses tmp_path but the function uses Path.home()
    # We're testing the function runs without error, not the exact path
    result = ensure_config_dir()
    assert result.exists()
    assert result.is_dir()


def test_load_valid_config(tmp_path):
    """Test loading a valid TOML config file."""
    # Create a valid config file
    config_file = tmp_path / "config.toml"
    config_content = """
[mcpx]
version = "1.0"

[servers.filesystem]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/projects"]

[servers.github]
command = "npx"
env = { TOKEN = "test" }
"""
    config_file.write_text(config_content)

    # Load the config
    config = load_config(config_file)

    # Verify structure
    assert config.version == "1.0"
    assert len(config.servers) == 2

    # Check filesystem server
    fs_server = config.servers["filesystem"]
    assert fs_server.name == "filesystem"
    assert fs_server.command == "npx"
    assert fs_server.args == ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/projects"]
    assert fs_server.env == {}

    # Check github server
    gh_server = config.servers["github"]
    assert gh_server.name == "github"
    assert gh_server.command == "npx"
    assert gh_server.args == []
    assert gh_server.env == {"TOKEN": "test"}


def test_load_minimal_config(tmp_path):
    """Test loading minimal valid config."""
    config_file = tmp_path / "config.toml"
    config_content = """
[mcpx]
version = "1.0"

[servers.test]
command = "echo"
"""
    config_file.write_text(config_content)

    config = load_config(config_file)

    assert config.version == "1.0"
    assert len(config.servers) == 1
    assert config.servers["test"].command == "echo"


def test_load_config_missing_file(tmp_path):
    """Test loading non-existent config file."""
    config_file = tmp_path / "nonexistent.toml"

    with pytest.raises(FileNotFoundError, match="Config file not found"):
        load_config(config_file)


def test_load_config_invalid_toml(tmp_path):
    """Test loading config with invalid TOML syntax."""
    config_file = tmp_path / "invalid.toml"
    config_file.write_text("[mcpx\nversion = '1.0'")  # Missing closing bracket

    with pytest.raises(tomllib.TOMLDecodeError):
        load_config(config_file)


def test_load_config_missing_mcpx_section(tmp_path):
    """Test config without [mcpx] section."""
    config_file = tmp_path / "invalid.toml"
    config_content = """
[servers.test]
command = "echo"
"""
    config_file.write_text(config_content)

    with pytest.raises(ValueError, match="Missing required \\[mcpx\\] section"):
        load_config(config_file)


def test_load_config_missing_version(tmp_path):
    """Test config without version field."""
    config_file = tmp_path / "invalid.toml"
    config_content = """
[mcpx]

[servers.test]
command = "echo"
"""
    config_file.write_text(config_content)

    with pytest.raises(ValueError, match="Missing required 'version' field"):
        load_config(config_file)


def test_load_config_missing_servers_section(tmp_path):
    """Test config without [servers] section."""
    config_file = tmp_path / "invalid.toml"
    config_content = """
[mcpx]
version = "1.0"
"""
    config_file.write_text(config_content)

    with pytest.raises(ValueError, match="Missing required \\[servers\\] section"):
        load_config(config_file)


def test_load_config_server_missing_command(tmp_path):
    """Test server definition without command field."""
    config_file = tmp_path / "invalid.toml"
    config_content = """
[mcpx]
version = "1.0"

[servers.test]
args = ["echo"]
"""
    config_file.write_text(config_content)

    with pytest.raises(ValueError, match="Server 'test' missing required 'command' field"):
        load_config(config_file)


def test_load_config_with_env_expansion(tmp_path, monkeypatch):
    """Test that environment variables are expanded during loading."""
    # Set test environment variables
    monkeypatch.setenv("HOME", "/home/testuser")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

    config_file = tmp_path / "config.toml"
    config_content = """
[mcpx]
version = "1.0"

[servers.filesystem]
command = "npx"
args = ["-y", "server", "${HOME}/projects"]
env = { TOKEN = "${GITHUB_TOKEN}" }
"""
    config_file.write_text(config_content)

    config = load_config(config_file)

    fs_server = config.servers["filesystem"]
    assert fs_server.args == ["-y", "server", "/home/testuser/projects"]
    assert fs_server.env == {"TOKEN": "ghp_test_token"}
