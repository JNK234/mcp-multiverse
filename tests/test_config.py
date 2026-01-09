# Tests for configuration loading
import json

import pytest

from mcpx.config import CONFIG_FILE, ensure_config_dir, get_config_path, load_config


def test_get_config_path():
    """Test getting config file path."""
    path = get_config_path()
    assert path == CONFIG_FILE
    assert path.name == "config.json"
    assert ".mcpx" in str(path)


def test_ensure_config_dir(tmp_path):
    """Test creating config directory."""
    # Note: This test uses tmp_path but the function uses Path.home()
    # We're testing the function runs without error, not the exact path
    result = ensure_config_dir()
    assert result.exists()
    assert result.is_dir()


def test_load_valid_config(tmp_path):
    """Test loading a valid JSON config file."""
    # Create a valid config file
    config_file = tmp_path / "config.json"
    config_content = {
        "mcpx": {
            "version": "1.0"
        },
        "servers": {
            "filesystem": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/projects"]
            },
            "github": {
                "type": "stdio",
                "command": "npx",
                "env": {"TOKEN": "test"}
            }
        }
    }
    config_file.write_text(json.dumps(config_content, indent=2))

    # Load the config
    config = load_config(config_file)

    # Verify structure
    assert config.version == "1.0"
    assert len(config.servers) == 2

    # Check filesystem server
    fs_server = config.servers["filesystem"]
    assert fs_server.name == "filesystem"
    assert fs_server.type == "stdio"
    assert fs_server.command == "npx"
    assert fs_server.args == ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/projects"]
    assert fs_server.env == {}

    # Check github server
    gh_server = config.servers["github"]
    assert gh_server.name == "github"
    assert gh_server.type == "stdio"
    assert gh_server.command == "npx"
    assert gh_server.args == []
    assert gh_server.env == {"TOKEN": "test"}


def test_load_minimal_config(tmp_path):
    """Test loading minimal valid config."""
    config_file = tmp_path / "config.json"
    config_content = {
        "mcpx": {
            "version": "1.0"
        },
        "servers": {
            "test": {
                "type": "stdio",
                "command": "echo"
            }
        }
    }
    config_file.write_text(json.dumps(config_content, indent=2))

    config = load_config(config_file)

    assert config.version == "1.0"
    assert len(config.servers) == 1
    assert config.servers["test"].command == "echo"


def test_load_config_missing_file(tmp_path):
    """Test loading non-existent config file."""
    config_file = tmp_path / "nonexistent.json"

    with pytest.raises(FileNotFoundError, match="Config file not found"):
        load_config(config_file)


def test_load_config_invalid_json(tmp_path):
    """Test loading config with invalid JSON syntax."""
    config_file = tmp_path / "invalid.json"
    config_file.write_text('{"mcpx": invalid}')  # Invalid JSON

    with pytest.raises(json.JSONDecodeError):
        load_config(config_file)


def test_load_config_missing_mcpx_section(tmp_path):
    """Test config without mcpx section."""
    config_file = tmp_path / "invalid.json"
    config_content = {
        "servers": {
            "test": {
                "type": "stdio",
                "command": "echo"
            }
        }
    }
    config_file.write_text(json.dumps(config_content, indent=2))

    with pytest.raises(ValueError, match="Missing required 'mcpx' section"):
        load_config(config_file)


def test_load_config_missing_version(tmp_path):
    """Test config without version field."""
    config_file = tmp_path / "invalid.json"
    config_content = {
        "mcpx": {},
        "servers": {
            "test": {
                "type": "stdio",
                "command": "echo"
            }
        }
    }
    config_file.write_text(json.dumps(config_content, indent=2))

    with pytest.raises(ValueError, match="Missing required 'version' field"):
        load_config(config_file)


def test_load_config_missing_servers_section(tmp_path):
    """Test config without servers section."""
    config_file = tmp_path / "invalid.json"
    config_content = {
        "mcpx": {
            "version": "1.0"
        }
    }
    config_file.write_text(json.dumps(config_content, indent=2))

    with pytest.raises(ValueError, match="Missing required 'servers' section"):
        load_config(config_file)


def test_load_config_server_missing_type(tmp_path):
    """Test server definition without type field (should auto-detect as stdio)."""
    config_file = tmp_path / "config.json"
    config_content = {
        "mcpx": {
            "version": "1.0"
        },
        "servers": {
            "test": {
                "command": "echo"
            }
        }
    }
    config_file.write_text(json.dumps(config_content, indent=2))

    # Should auto-detect as stdio (has command field)
    config = load_config(config_file)
    assert "test" in config.servers
    assert config.servers["test"].type == "stdio"
    assert config.servers["test"].command == "echo"


def test_load_config_server_missing_command(tmp_path):
    """Test stdio server definition without command field."""
    config_file = tmp_path / "invalid.json"
    config_content = {
        "mcpx": {
            "version": "1.0"
        },
        "servers": {
            "test": {
                "type": "stdio",
                "args": ["echo"]
            }
        }
    }
    config_file.write_text(json.dumps(config_content, indent=2))

    with pytest.raises(ValueError, match="Server 'test' missing required 'command' field"):
        load_config(config_file)


def test_load_config_with_env_expansion(tmp_path, monkeypatch):
    """Test that environment variables are expanded during loading."""
    # Set test environment variables
    monkeypatch.setenv("HOME", "/home/testuser")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

    config_file = tmp_path / "config.json"
    config_content = {
        "mcpx": {
            "version": "1.0"
        },
        "servers": {
            "filesystem": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "server", "${HOME}/projects"],
                "env": {"TOKEN": "${GITHUB_TOKEN}"}
            }
        }
    }
    config_file.write_text(json.dumps(config_content, indent=2))

    config = load_config(config_file)

    fs_server = config.servers["filesystem"]
    assert fs_server.args == ["-y", "server", "/home/testuser/projects"]
    assert fs_server.env == {"TOKEN": "ghp_test_token"}


def test_load_http_server(tmp_path):
    """Test loading HTTP server type."""
    config_file = tmp_path / "config.json"
    config_content = {
        "mcpx": {
            "version": "1.0"
        },
        "servers": {
            "api_server": {
                "type": "http",
                "url": "https://api.example.com/mcp",
                "headers": {"Authorization": "Bearer token"}
            }
        }
    }
    config_file.write_text(json.dumps(config_content, indent=2))

    config = load_config(config_file)

    api_server = config.servers["api_server"]
    assert api_server.name == "api_server"
    assert api_server.type == "http"
    assert api_server.url == "https://api.example.com/mcp"
    assert api_server.headers == {"Authorization": "Bearer token"}


def test_load_http_server_missing_url(tmp_path):
    """Test HTTP server without required url field."""
    config_file = tmp_path / "invalid.json"
    config_content = {
        "mcpx": {
            "version": "1.0"
        },
        "servers": {
            "api_server": {
                "type": "http"
            }
        }
    }
    config_file.write_text(json.dumps(config_content, indent=2))

    with pytest.raises(ValueError, match="Server 'api_server' missing required 'url' field"):
        load_config(config_file)


def test_load_invalid_server_type(tmp_path):
    """Test server with invalid type."""
    config_file = tmp_path / "invalid.json"
    config_content = {
        "mcpx": {
            "version": "1.0"
        },
        "servers": {
            "test": {
                "type": "invalid_type",
                "command": "echo"
            }
        }
    }
    config_file.write_text(json.dumps(config_content, indent=2))

    with pytest.raises(ValueError, match="invalid type 'invalid_type'"):
        load_config(config_file)
