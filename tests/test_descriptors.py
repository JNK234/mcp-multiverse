# ABOUTME: Per-descriptor MCP shape tests for Codex/OpenCode/Cline/Kilo (data-driven).
# ABOUTME: Covers the two fixed bugs (Cline autoApprove, Codex HTTP) and tricky transforms.
import dataclasses

from mcpx.descriptors import REGISTRY
from mcpx.descriptors.cline import CLINE
from mcpx.descriptors.codex import CODEX
from mcpx.descriptors.kilo import KILO
from mcpx.descriptors.opencode import OPENCODE
from mcpx.engine.mapping import apply_field_maps_to_ir, render_native_from_ir
from mcpx.ir import MCPServerIR, Transport


def _stdio() -> MCPServerIR:
    return MCPServerIR(
        name="github", transport=Transport.STDIO, command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"},
        auto_approve=["read_file"],
    )


def _http() -> MCPServerIR:
    return MCPServerIR(
        name="supabase", transport=Transport.HTTP, url="https://mcp.supabase.com/mcp",
        headers={"X-Org": "acme"}, bearer_token_env_var="SUPABASE_TOKEN",
    )


def test_registry_has_all_six() -> None:
    assert set(REGISTRY) == {"claude", "gemini", "codex", "opencode", "cline", "kilo"}


# --- OpenCode: command-array, environment, local/remote, enabled -------

def test_opencode_stdio_command_array_and_environment() -> None:
    native = render_native_from_ir(OPENCODE.mcp, "opencode", _stdio())
    assert native["type"] == "local"
    # command + args merged into a single array
    assert native["command"] == ["npx", "-y", "@modelcontextprotocol/server-github"]
    # env renamed to environment
    assert native["environment"] == {"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"}
    assert "env" not in native and "args" not in native
    assert native["enabled"] is True


def test_opencode_http_is_remote() -> None:
    native = render_native_from_ir(OPENCODE.mcp, "opencode", _http())
    assert native["type"] == "remote"
    assert native["url"] == "https://mcp.supabase.com/mcp"


def test_opencode_roundtrip_splits_command_array() -> None:
    server = _stdio()
    native = render_native_from_ir(OPENCODE.mcp, "opencode", server)
    back = apply_field_maps_to_ir(OPENCODE.mcp, "opencode", "github", native)
    assert back.command == "npx"
    assert back.args == ["-y", "@modelcontextprotocol/server-github"]
    assert back.transport is Transport.STDIO
    assert back.env == {"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"}


# --- Codex: HTTP supported (bug fix), bearer, no type key --------------

def test_codex_http_supported_with_bearer() -> None:
    assert CODEX.mcp.supports_http is True
    native = render_native_from_ir(CODEX.mcp, "codex", _http())
    assert native["url"] == "https://mcp.supabase.com/mcp"
    assert native["http_headers"] == {"X-Org": "acme"}
    assert native["bearer_token_env_var"] == "SUPABASE_TOKEN"
    # Codex has no `type` discriminator
    assert "type" not in native


def test_codex_stdio_no_type_key() -> None:
    native = render_native_from_ir(CODEX.mcp, "codex", _stdio())
    assert native["command"] == "npx"
    assert "type" not in native


def test_codex_transport_inferred_on_read() -> None:
    http_back = apply_field_maps_to_ir(CODEX.mcp, "codex", "s", {"url": "https://x/mcp"})
    assert http_back.transport is Transport.HTTP
    stdio_back = apply_field_maps_to_ir(CODEX.mcp, "codex", "s", {"command": "npx"})
    assert stdio_back.transport is Transport.STDIO


# --- Cline: autoApprove (bug fix), streamableHttp (#6767), disabled ----

def test_cline_writes_auto_approve_not_always_allow() -> None:
    native = render_native_from_ir(CLINE.mcp, "cline", _stdio())
    assert native["autoApprove"] == ["read_file"]
    assert "alwaysAllow" not in native


def test_cline_remote_uses_streamable_http() -> None:
    native = render_native_from_ir(CLINE.mcp, "cline", _http())
    assert native["type"] == "streamableHttp"


def test_cline_stdio_has_disabled_default() -> None:
    native = render_native_from_ir(CLINE.mcp, "cline", _stdio())
    assert native["type"] == "stdio"
    assert native["disabled"] is False


# --- Kilo: alwaysAllow (Roo/Kilo terminology) -------------------------

def test_kilo_uses_always_allow() -> None:
    native = render_native_from_ir(KILO.mcp, "kilo", _stdio())
    assert native["alwaysAllow"] == ["read_file"]
    assert "autoApprove" not in native
    assert native["disabled"] is False


# --- secrets verbatim across all tools --------------------------------

def test_all_tools_keep_secret_refs_verbatim() -> None:
    for tool_id in ("claude", "gemini", "codex", "opencode", "cline", "kilo"):
        spec = REGISTRY[tool_id].mcp
        native = render_native_from_ir(spec, tool_id, _stdio())
        env = native.get("env") or native.get("environment") or {}
        assert env.get("GITHUB_PERSONAL_ACCESS_TOKEN") == "${GITHUB_TOKEN}"


def test_descriptors_are_frozen_data() -> None:
    """Descriptors must be immutable data objects (frozen dataclasses)."""
    for desc in REGISTRY.values():
        assert dataclasses.is_dataclass(desc)
        # frozen => cannot set attribute
        try:
            desc.id = "x"  # type: ignore[misc]
            raise AssertionError("descriptor should be frozen")
        except dataclasses.FrozenInstanceError:
            pass
