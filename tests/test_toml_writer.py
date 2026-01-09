# Tests for minimal TOML writer utility
from pathlib import Path

from mcpx.utils.toml_writer import _format_array, _format_inline_table, write_toml_simple


def test_write_toml_simple_basic(tmp_path: Path) -> None:
    """Test basic TOML writing."""
    output_file = tmp_path / "config.toml"

    data = {
        "mcp_servers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem"],
            }
        }
    }

    write_toml_simple(data, output_file)

    content = output_file.read_text()
    assert "[mcp_servers.filesystem]" in content
    assert 'command = "npx"' in content
    assert 'args = ["-y", "@modelcontextprotocol/server-filesystem"]' in content


def test_write_toml_with_env(tmp_path: Path) -> None:
    """Test TOML writing with environment variables."""
    output_file = tmp_path / "config.toml"

    data = {
        "mcp_servers": {
            "github": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_TOKEN": "ghp_xxxx"},
            }
        }
    }

    write_toml_simple(data, output_file)

    content = output_file.read_text()
    assert 'env = { GITHUB_TOKEN = "ghp_xxxx" }' in content


def test_write_toml_multiple_servers(tmp_path: Path) -> None:
    """Test writing multiple servers."""
    output_file = tmp_path / "config.toml"

    data = {
        "mcp_servers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"],
            },
            "github": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"TOKEN": "value"},
            },
        }
    }

    write_toml_simple(data, output_file)

    content = output_file.read_text()
    assert "[mcp_servers.filesystem]" in content
    assert "[mcp_servers.github]" in content


def test_write_toml_creates_parent_dirs(tmp_path: Path) -> None:
    """Test that parent directories are created."""
    output_file = tmp_path / "nested" / "dir" / "config.toml"

    data = {"mcp_servers": {}}

    write_toml_simple(data, output_file)

    assert output_file.exists()
    assert output_file.parent.exists()


def test_format_array_strings() -> None:
    """Test formatting string arrays."""
    result = _format_array(["-y", "@modelcontextprotocol/server-filesystem"])
    assert result == '["-y", "@modelcontextprotocol/server-filesystem"]'


def test_format_array_empty() -> None:
    """Test formatting empty array."""
    result = _format_array([])
    assert result == "[]"


def test_format_array_with_quotes() -> None:
    """Test escaping quotes in array items."""
    result = _format_array(['cmd "with" quotes', 'another'])
    assert result == '["cmd \\"with\\" quotes", "another"]'


def test_format_array_with_backslashes() -> None:
    """Test escaping backslashes in array items."""
    result = _format_array(["path\\to\\file", "normal"])
    assert result == '["path\\\\to\\\\file", "normal"]'


def test_format_inline_table_basic() -> None:
    """Test formatting inline tables."""
    result = _format_inline_table({"KEY": "value"})
    assert result == '{ KEY = "value" }'


def test_format_inline_table_multiple_keys() -> None:
    """Test formatting inline table with multiple keys."""
    result = _format_inline_table({"KEY1": "val1", "KEY2": "val2"})
    assert result == '{ KEY1 = "val1", KEY2 = "val2" }'


def test_format_inline_table_empty() -> None:
    """Test formatting empty inline table."""
    result = _format_inline_table({})
    assert result == "{}"


def test_format_inline_table_with_quotes() -> None:
    """Test escaping quotes in inline table values."""
    result = _format_inline_table({"KEY": 'value "with" quotes'})
    assert result == '{ KEY = "value \\"with\\" quotes" }'


def test_write_toml_spec_format(tmp_path: Path) -> None:
    """Test output matches specification format exactly."""
    output_file = tmp_path / "config.toml"

    data = {
        "mcp_servers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/user/projects"],
            },
            "github": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxxx"},
            },
        }
    }

    write_toml_simple(data, output_file)

    content = output_file.read_text()

    # Verify exact format from spec
    assert '[mcp_servers.filesystem]' in content
    assert 'command = "npx"' in content
    expected_args = (
        'args = ["-y", "@modelcontextprotocol/server-filesystem", '
        '"/Users/user/projects"]'
    )
    assert expected_args in content

    assert '[mcp_servers.github]' in content
    assert 'command = "npx"' in content
    assert 'args = ["-y", "@modelcontextprotocol/server-github"]' in content
    assert 'env = { GITHUB_PERSONAL_ACCESS_TOKEN = "ghp_xxxx" }' in content


def test_write_toml_trailing_newline(tmp_path: Path) -> None:
    """Test that output ends with single newline."""
    output_file = tmp_path / "config.toml"

    data = {
        "mcp_servers": {
            "test": {
                "command": "node",
                "args": [],
            }
        }
    }

    write_toml_simple(data, output_file)

    content = output_file.read_text()
    assert content.endswith("\n")
    # Should not have double newline at end
    assert not content.endswith("\n\n")
