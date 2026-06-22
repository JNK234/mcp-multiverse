# ABOUTME: Tests for the generic MCP engine + Claude/Gemini descriptors + port orchestration.
# ABOUTME: Verifies IR<->native round-trips, foreign-key preservation, HTTP handling, dry-run.
import json
from pathlib import Path

from mcpx.descriptors import REGISTRY
from mcpx.descriptors.claude import CLAUDE
from mcpx.descriptors.gemini import GEMINI
from mcpx.engine import export_mcp, import_mcp
from mcpx.engine.mapping import apply_field_maps_to_ir, render_native_from_ir
from mcpx.ir import MCPServerIR, Transport


def _stdio() -> MCPServerIR:
    return MCPServerIR(
        name="github",
        transport=Transport.STDIO,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"},
    )


def _http() -> MCPServerIR:
    return MCPServerIR(name="supabase", transport=Transport.HTTP, url="https://mcp.supabase.com/mcp")


# --- mapping round-trips (Claude) ---------------------------------------

def test_claude_render_stdio() -> None:
    native = render_native_from_ir(CLAUDE.mcp, "claude", _stdio())
    assert native == {
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"},
    }


def test_claude_render_http() -> None:
    native = render_native_from_ir(CLAUDE.mcp, "claude", _http())
    assert native == {"type": "http", "url": "https://mcp.supabase.com/mcp"}


def test_claude_mapping_roundtrip() -> None:
    server = _stdio()
    native = render_native_from_ir(CLAUDE.mcp, "claude", server)
    back = apply_field_maps_to_ir(CLAUDE.mcp, "claude", "github", native)
    assert back == server


def test_secret_ref_written_verbatim() -> None:
    """Secrets policy: ${VAR} must pass through unexpanded."""
    native = render_native_from_ir(CLAUDE.mcp, "claude", _stdio())
    assert native["env"]["GITHUB_PERSONAL_ACCESS_TOKEN"] == "${GITHUB_TOKEN}"


def test_unmapped_native_keys_preserved_in_extra() -> None:
    """A native key with no FieldMap is kept in extra[tool_id] for lossless re-export."""
    native = {"type": "stdio", "command": "x", "timeout": 60, "weirdField": True}
    ir = apply_field_maps_to_ir(CLAUDE.mcp, "claude", "x", native)
    assert ir.extra["claude"] == {"timeout": 60, "weirdField": True}
    # And re-export restores them.
    back = render_native_from_ir(CLAUDE.mcp, "claude", ir)
    assert back["timeout"] == 60 and back["weirdField"] is True


# --- import / export against real files ---------------------------------

def test_import_mcp_from_claude_json(tmp_path: Path) -> None:
    claude_file = tmp_path / ".claude.json"
    claude_file.write_text(json.dumps({
        "mcpServers": {
            "github": {"type": "stdio", "command": "npx", "args": ["-y", "gh"]},
            "supa": {"type": "http", "url": "https://x/mcp"},
        },
        "someOtherState": {"keep": True},
    }))
    desc = CLAUDE.__class__(
        id="claude", display_name="Claude Code",
        config_paths={"mcp": str(claude_file)}, fmt="json", mcp=CLAUDE.mcp,
    )
    servers = import_mcp(desc)
    assert set(servers) == {"github", "supa"}
    assert servers["github"].command == "npx"
    assert servers["supa"].transport is Transport.HTTP


def test_export_preserves_foreign_keys(tmp_path: Path) -> None:
    """Gemini export must leave selectedAuthType/theme untouched."""
    gem_file = tmp_path / "settings.json"
    gem_file.write_text(json.dumps({"selectedAuthType": "oauth", "theme": "dark"}))
    desc = GEMINI.__class__(
        id="gemini", display_name="Gemini CLI",
        config_paths={"mcp": str(gem_file)}, fmt="json", mcp=GEMINI.mcp,
    )
    export_mcp(desc, {"github": _stdio()}, dry_run=False)
    data = json.loads(gem_file.read_text())
    assert data["selectedAuthType"] == "oauth"
    assert data["theme"] == "dark"
    assert data["mcpServers"]["github"]["command"] == "npx"


def test_export_dry_run_writes_nothing(tmp_path: Path) -> None:
    gem_file = tmp_path / "settings.json"
    desc = GEMINI.__class__(
        id="gemini", display_name="Gemini CLI",
        config_paths={"mcp": str(gem_file)}, fmt="json", mcp=GEMINI.mcp,
    )
    result = export_mcp(desc, {"github": _stdio()}, dry_run=True)
    assert not gem_file.exists()
    assert "github" in result.written


def test_port_to_target(tmp_path: Path) -> None:
    gem_file = tmp_path / "settings.json"
    desc = GEMINI.__class__(
        id="gemini", display_name="Gemini CLI",
        config_paths={"mcp": str(gem_file)}, fmt="json", mcp=GEMINI.mcp,
    )
    # Inject into a temporary registry view via direct export (port uses REGISTRY,
    # so here we test the engine path the orchestrator delegates to).
    result = export_mcp(desc, {"github": _stdio(), "supa": _http()}, dry_run=False)
    assert set(result.written) == {"github", "supa"}
    assert gem_file.exists()


def test_registry_has_claude_and_gemini() -> None:
    assert "claude" in REGISTRY
    assert "gemini" in REGISTRY
    assert REGISTRY["claude"].mcp is not None
