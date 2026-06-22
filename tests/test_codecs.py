# ABOUTME: Tests for format codecs (json/jsonc/toml) — round-trips and foreign-key preservation.
# ABOUTME: Verifies jsonc preserves $schema/comments-on-read and toml renders HTTP + bearer servers.
from pathlib import Path

import pytest

from mcpx.codecs import codec_for
from mcpx.codecs.json_codec import JsonCodec
from mcpx.codecs.jsonc_codec import JsoncCodec
from mcpx.codecs.toml_codec import TomlCodec


def test_codec_for_returns_correct_codecs() -> None:
    assert isinstance(codec_for("json"), JsonCodec)
    assert isinstance(codec_for("jsonc"), JsoncCodec)
    assert isinstance(codec_for("toml-flat"), TomlCodec)
    assert isinstance(codec_for("toml"), TomlCodec)


def test_codec_for_unknown_raises() -> None:
    with pytest.raises(ValueError, match="No codec registered"):
        codec_for("nonsense")


# --- JSON codec ---------------------------------------------------------

def test_json_read_missing_returns_empty(tmp_path: Path) -> None:
    assert JsonCodec().read(tmp_path / "nope.json") == {}


def test_json_roundtrip_preserves_order(tmp_path: Path) -> None:
    path = tmp_path / "c.json"
    data = {"zebra": 1, "apple": 2, "mango": {"x": [1, 2]}}
    JsonCodec().write(path, data)
    # Keys must NOT be sorted (idempotency) — zebra stays first.
    text = path.read_text()
    assert text.index('"zebra"') < text.index('"apple"')
    assert JsonCodec().read(path) == data


def test_json_invalid_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{ not json ")
    with pytest.raises(ValueError, match="Invalid JSON"):
        JsonCodec().read(path)


# --- JSONC codec --------------------------------------------------------

def test_jsonc_strips_comments_and_keeps_schema(tmp_path: Path) -> None:
    path = tmp_path / "opencode.jsonc"
    path.write_text(
        '{\n'
        '  // a line comment\n'
        '  "$schema": "https://opencode.ai/config.json",\n'
        '  /* block */ "mcp": { "x": { "type": "local" } },\n'
        '}\n'  # trailing comma
    )
    data = JsoncCodec().read(path)
    assert data["$schema"] == "https://opencode.ai/config.json"
    assert data["mcp"] == {"x": {"type": "local"}}


def test_jsonc_does_not_corrupt_urls_with_slashes(tmp_path: Path) -> None:
    path = tmp_path / "x.jsonc"
    path.write_text('{ "url": "https://mcp.example.com/mcp" }')
    data = JsoncCodec().read(path)
    assert data["url"] == "https://mcp.example.com/mcp"


def test_jsonc_write_then_read_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "x.jsonc"
    data = {"$schema": "s", "mcp": {"a": {"type": "remote", "url": "u"}}}
    JsoncCodec().write(path, data)
    assert JsoncCodec().read(path) == data


# --- TOML codec ---------------------------------------------------------

def test_toml_write_stdio_server(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    data = {
        "mcp_servers": {
            "github": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxxx"},
            }
        }
    }
    TomlCodec().write(path, data)
    content = path.read_text()
    assert "[mcp_servers.github]" in content
    assert 'command = "npx"' in content
    assert 'args = ["-y", "@modelcontextprotocol/server-github"]' in content
    assert 'env = { GITHUB_PERSONAL_ACCESS_TOKEN = "ghp_xxxx" }' in content


def test_toml_write_http_server_with_bearer(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    data = {
        "mcp_servers": {
            "supabase": {
                "url": "https://mcp.supabase.com/mcp",
                "http_headers": {"X-Org": "acme"},
                "bearer_token_env_var": "SUPABASE_TOKEN",
            }
        }
    }
    TomlCodec().write(path, data)
    content = path.read_text()
    assert "[mcp_servers.supabase]" in content
    assert 'url = "https://mcp.supabase.com/mcp"' in content
    assert 'http_headers = { X-Org = "acme" }' in content
    assert 'bearer_token_env_var = "SUPABASE_TOKEN"' in content
    # No stdio keys should leak in
    assert "command =" not in content


def test_toml_preserves_foreign_sections(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        'model = "gpt-5.4"\n'
        'approval_policy = "on-request"\n\n'
        '[mcp_servers.old]\n'
        'command = "old-bin"\n\n'
        '[history]\n'
        'persistence = "save-all"\n'
    )
    TomlCodec().write(path, {"mcp_servers": {"new": {"command": "new-bin"}}})
    content = path.read_text()
    # Foreign top-level keys + [history] table survive; old mcp_servers replaced.
    assert 'model = "gpt-5.4"' in content
    assert 'approval_policy = "on-request"' in content
    assert "[history]" in content
    assert 'persistence = "save-all"' in content
    assert "[mcp_servers.new]" in content
    assert "[mcp_servers.old]" not in content


def test_toml_read_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    TomlCodec().write(path, {"mcp_servers": {"a": {"command": "x", "args": ["-y"]}}})
    parsed = TomlCodec().read(path)
    assert parsed["mcp_servers"]["a"]["command"] == "x"
    assert parsed["mcp_servers"]["a"]["args"] == ["-y"]


def test_toml_env_vars_written_verbatim(tmp_path: Path) -> None:
    """Secrets policy: ${VAR} references must be written literally, not expanded."""
    path = tmp_path / "config.toml"
    data = {"mcp_servers": {"gh": {"command": "npx", "env": {"TOKEN": "${GITHUB_TOKEN}"}}}}
    TomlCodec().write(path, data)
    assert 'env = { TOKEN = "${GITHUB_TOKEN}" }' in path.read_text()
