# ABOUTME: Tests for the new IR-based CLI commands: mcpx import / port / list.
# ABOUTME: Written test-first (TDD). Patches manifest path + descriptor config paths to tmp.
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mcpx.cli import EXIT_CONFIG_ERROR, EXIT_SUCCESS, cmd_import, cmd_list, cmd_port


@pytest.fixture
def fake_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Build a fake home with Claude (source) + Gemini/Codex targets, all path-redirected.

    ABOUTME: Returns an object with paths; patches each descriptor's mcp path to tmp and
    ABOUTME: the manifest path to tmp, so commands never touch the real home.
    """
    claude_file = tmp_path / "claude.json"
    claude_file.write_text(json.dumps({
        "mcpServers": {
            "github": {"type": "stdio", "command": "npx", "args": ["-y", "gh"]},
            "supa": {"type": "http", "url": "https://x/mcp"},
        }
    }))
    gemini_file = tmp_path / "gemini-settings.json"
    gemini_file.parent.mkdir(parents=True, exist_ok=True)
    gemini_file.write_text(json.dumps({"theme": "dark"}))
    codex_file = tmp_path / "codex.toml"
    codex_file.write_text("")  # exists => codex 'installed'
    manifest_file = tmp_path / "manifest.json"

    paths = {
        "claude": claude_file,
        "gemini": gemini_file,
        "codex": codex_file,
    }

    def fake_resolve(desc, logical="mcp"):
        return paths.get(desc.id, tmp_path / f"{desc.id}-missing.json")

    # Redirect path resolution everywhere it's used.
    monkeypatch.setattr("mcpx.engine.mcp_engine.resolve_path", fake_resolve)
    monkeypatch.setattr("mcpx.port.resolve_path", fake_resolve, raising=False)
    monkeypatch.setattr("mcpx.manifest.get_manifest_path", lambda: manifest_file)
    monkeypatch.setattr("mcpx.cli.get_manifest_path", lambda: manifest_file, raising=False)

    return SimpleNamespace(
        tmp=tmp_path, manifest=manifest_file, claude=claude_file,
        gemini=gemini_file, codex=codex_file,
    )


# --- mcpx import --------------------------------------------------------

def test_import_writes_manifest_from_claude(fake_tools, capsys) -> None:
    args = SimpleNamespace(source="claude")
    rc = cmd_import(args)
    assert rc == EXIT_SUCCESS
    assert fake_tools.manifest.exists()
    data = json.loads(fake_tools.manifest.read_text())
    assert set(data["servers"]) == {"github", "supa"}
    out = capsys.readouterr().out
    assert "2" in out  # reports 2 servers


def test_import_unknown_source_errors(fake_tools) -> None:
    args = SimpleNamespace(source="nonsense")
    rc = cmd_import(args)
    assert rc == EXIT_CONFIG_ERROR


# --- mcpx list ----------------------------------------------------------

def test_list_shows_servers_from_manifest(fake_tools, capsys) -> None:
    cmd_import(SimpleNamespace(source="claude"))
    rc = cmd_list(SimpleNamespace())
    assert rc == EXIT_SUCCESS
    out = capsys.readouterr().out
    assert "github" in out
    assert "supa" in out


def test_list_without_manifest_errors(fake_tools) -> None:
    rc = cmd_list(SimpleNamespace())
    assert rc == EXIT_CONFIG_ERROR


# --- mcpx port ----------------------------------------------------------

def test_port_dry_run_writes_nothing(fake_tools, capsys) -> None:
    cmd_import(SimpleNamespace(source="claude"))
    args = SimpleNamespace(source="claude", to="gemini", dry_run=True, yes=True)
    rc = cmd_port(args)
    assert rc == EXIT_SUCCESS
    # Gemini file unchanged (still just theme, no mcpServers written)
    data = json.loads(fake_tools.gemini.read_text())
    assert "mcpServers" not in data
    out = capsys.readouterr().out
    assert "dry" in out.lower() or "would" in out.lower()


def test_port_writes_to_target(fake_tools) -> None:
    cmd_import(SimpleNamespace(source="claude"))
    args = SimpleNamespace(source="claude", to="gemini", dry_run=False, yes=True)
    rc = cmd_port(args)
    assert rc == EXIT_SUCCESS
    data = json.loads(fake_tools.gemini.read_text())
    assert data["theme"] == "dark"  # foreign key preserved
    assert set(data["mcpServers"]) == {"github", "supa"}


def test_port_all_targets_defaults_to_installed(fake_tools) -> None:
    cmd_import(SimpleNamespace(source="claude"))
    # to=None => all installed targets (gemini + codex have files; others absent)
    args = SimpleNamespace(source="claude", to=None, dry_run=False, yes=True)
    rc = cmd_port(args)
    assert rc == EXIT_SUCCESS
    # Gemini got servers
    assert "mcpServers" in json.loads(fake_tools.gemini.read_text())
    # Codex got the TOML section
    assert "[mcp_servers.github]" in fake_tools.codex.read_text()


def test_port_without_manifest_errors(fake_tools) -> None:
    args = SimpleNamespace(source="claude", to="gemini", dry_run=False, yes=True)
    rc = cmd_port(args)
    assert rc == EXIT_CONFIG_ERROR


def test_port_unknown_target_errors(fake_tools) -> None:
    cmd_import(SimpleNamespace(source="claude"))
    args = SimpleNamespace(source="claude", to="nonsense", dry_run=False, yes=True)
    rc = cmd_port(args)
    assert rc == EXIT_CONFIG_ERROR
