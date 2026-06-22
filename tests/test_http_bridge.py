# ABOUTME: Tests for the HTTP->mcp-remote stdio bridge (Codex can't handshake SSE HTTP servers).
# ABOUTME: Written test-first. An MCPSpec with http_bridge renders HTTP servers as stdio commands.
from mcpx.descriptors import REGISTRY
from mcpx.descriptors.codex import CODEX
from mcpx.engine.mapping import render_native_from_ir
from mcpx.ir import MCPServerIR, Transport


def _http_with_bearer() -> MCPServerIR:
    return MCPServerIR(
        name="web-search-prime",
        transport=Transport.HTTP,
        url="https://api.z.ai/api/mcp/web_search_prime/mcp",
        headers={"Authorization": "Bearer ${ZAI_API_KEY}"},
    )


def _http_no_headers() -> MCPServerIR:
    return MCPServerIR(
        name="plain",
        transport=Transport.HTTP,
        url="https://example.com/mcp",
    )


def _stdio() -> MCPServerIR:
    return MCPServerIR(
        name="github", transport=Transport.STDIO, command="npx", args=["-y", "gh"],
    )


# --- Codex HTTP servers render as mcp-remote bridge ---------------------

def test_codex_http_server_renders_as_mcp_remote_bridge() -> None:
    native = render_native_from_ir(CODEX.mcp, "codex", _http_with_bearer())
    # Becomes a stdio command, NOT a url server.
    assert native["command"] == "npx"
    assert "url" not in native
    assert native["args"][:3] == ["-y", "mcp-remote", "https://api.z.ai/api/mcp/web_search_prime/mcp"]
    # The Authorization header is passed through as a --header arg, verbatim ${VAR}.
    assert "--header" in native["args"]
    hdr_idx = native["args"].index("--header")
    assert native["args"][hdr_idx + 1] == "Authorization: Bearer ${ZAI_API_KEY}"


def test_codex_http_server_without_headers_still_bridges() -> None:
    native = render_native_from_ir(CODEX.mcp, "codex", _http_no_headers())
    assert native["command"] == "npx"
    assert native["args"][:3] == ["-y", "mcp-remote", "https://example.com/mcp"]
    # No headers -> no --header arg
    assert "--header" not in native["args"]


def test_codex_stdio_server_unaffected_by_bridge() -> None:
    """The bridge only applies to HTTP servers; stdio servers pass through normally."""
    native = render_native_from_ir(CODEX.mcp, "codex", _stdio())
    assert native["command"] == "npx"
    assert native["args"] == ["-y", "gh"]


def test_codex_supports_http_true_so_not_skipped() -> None:
    """Codex must still 'support' HTTP (so HTTP servers aren't skipped) — it bridges them."""
    assert CODEX.mcp.supports_http is True


# --- other tools must NOT bridge (they handle native HTTP fine) ---------

def test_opencode_http_stays_native_remote() -> None:
    native = render_native_from_ir(REGISTRY["opencode"].mcp, "opencode", _http_with_bearer())
    assert native["type"] == "remote"
    assert native["url"] == "https://api.z.ai/api/mcp/web_search_prime/mcp"
    assert "command" not in native


def test_cline_http_stays_native() -> None:
    native = render_native_from_ir(REGISTRY["cline"].mcp, "cline", _http_with_bearer())
    assert native["url"] == "https://api.z.ai/api/mcp/web_search_prime/mcp"
    assert native["type"] == "streamableHttp"
    assert "command" not in native
