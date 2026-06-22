# ABOUTME: Tests for the IR manifest (load/save ~/.mcpx/manifest.json) and IR serialization.
# ABOUTME: Verifies MCPServerIR round-trips losslessly including the namespaced `extra` field.
from pathlib import Path

from mcpx.ir import Manifest, MCPServerIR, Transport
from mcpx.manifest import (
    MANIFEST_VERSION,
    load_manifest,
    save_manifest,
    server_from_dict,
    server_to_dict,
)


def test_stdio_server_roundtrip() -> None:
    server = MCPServerIR(
        name="github",
        transport=Transport.STDIO,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"},
    )
    restored = server_from_dict("github", server_to_dict(server))
    assert restored == server


def test_http_server_roundtrip() -> None:
    server = MCPServerIR(
        name="supabase",
        transport=Transport.HTTP,
        url="https://mcp.supabase.com/mcp",
        headers={"Authorization": "Bearer ${API_TOKEN}"},
        bearer_token_env_var="API_TOKEN",
    )
    restored = server_from_dict("supabase", server_to_dict(server))
    assert restored == server


def test_extra_namespaced_roundtrip() -> None:
    """The `extra` escape hatch (native fields with no IR home) must survive round-trip."""
    server = MCPServerIR(
        name="x",
        transport=Transport.STDIO,
        command="x",
        disabled=True,
        auto_approve=["read_file"],
        extra={"cline": {"timeout": 60}, "codex": {"startup_timeout_ms": 10000}},
    )
    restored = server_from_dict("x", server_to_dict(server))
    assert restored == server
    assert restored.extra["cline"]["timeout"] == 60


def test_server_to_dict_omits_empty_fields() -> None:
    server = MCPServerIR(name="x", transport=Transport.STDIO, command="x")
    data = server_to_dict(server)
    assert data == {"transport": "stdio", "command": "x"}
    assert "args" not in data and "env" not in data and "disabled" not in data


def test_transport_inferred_from_url_when_missing() -> None:
    server = server_from_dict("s", {"url": "https://x/mcp"})
    assert server.transport is Transport.HTTP


def test_load_missing_manifest_returns_empty(tmp_path: Path) -> None:
    manifest = load_manifest(tmp_path / "manifest.json")
    assert manifest.version == MANIFEST_VERSION
    assert manifest.servers == {}


def test_manifest_save_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    manifest = Manifest(
        version="2.0",
        servers={
            "github": MCPServerIR(
                name="github", transport=Transport.STDIO, command="npx", args=["-y", "gh"]
            ),
            "supabase": MCPServerIR(
                name="supabase", transport=Transport.HTTP, url="https://x/mcp"
            ),
        },
    )
    save_manifest(manifest, path)
    loaded = load_manifest(path)
    assert loaded.version == "2.0"
    assert set(loaded.servers) == {"github", "supabase"}
    assert loaded.servers["github"].command == "npx"
    assert loaded.servers["supabase"].transport is Transport.HTTP
