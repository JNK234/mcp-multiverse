# ABOUTME: Tests for the skills CLI: mcpx import --skills / list --skills / port --kind skills.
# ABOUTME: Written test-first. Patches skills store + descriptor skills paths to tmp.
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mcpx.cli import EXIT_CONFIG_ERROR, EXIT_SUCCESS, cmd_import, cmd_list, cmd_port


@pytest.fixture
def fake_skills(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Fake Claude skills source + OpenCode target + an isolated store, all path-redirected."""
    claude_skills = tmp_path / "claude-skills"
    for name in ("alpha", "beta"):
        d = claude_skills / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: d\nmodel: opus\n---\nBody {name}.\n"
        )
    opencode_skills = tmp_path / "opencode-skills"
    store = tmp_path / "store" / "skills"
    manifest = tmp_path / "manifest.json"

    paths = {"claude": claude_skills, "opencode": opencode_skills}

    def fake_resolve(desc, logical="mcp"):
        if logical == "skills":
            return paths.get(desc.id, tmp_path / f"{desc.id}-skills")
        return tmp_path / f"{desc.id}-{logical}"

    monkeypatch.setattr("mcpx.engine.mcp_engine.resolve_path", fake_resolve)
    monkeypatch.setattr("mcpx.engine.skills_engine.resolve_path", fake_resolve)
    monkeypatch.setattr("mcpx.manifest.get_skills_store_dir", lambda: store)
    monkeypatch.setattr("mcpx.cli.get_skills_store_dir", lambda: store, raising=False)
    monkeypatch.setattr("mcpx.manifest.get_manifest_path", lambda: manifest)
    monkeypatch.setattr("mcpx.cli.get_manifest_path", lambda: manifest, raising=False)
    monkeypatch.setattr("mcpx.engine.skills_engine.get_backup_dir", lambda: tmp_path / "bk")
    # Only opencode is "installed" for auto-target detection
    monkeypatch.setattr(
        "mcpx.port.installed_targets",
        lambda exclude=None: ["opencode"], raising=False,
    )

    return SimpleNamespace(
        claude=claude_skills, opencode=opencode_skills, store=store, manifest=manifest,
    )


def test_import_skills_populates_store(fake_skills, capsys) -> None:
    rc = cmd_import(SimpleNamespace(source="claude", skills=True))
    assert rc == EXIT_SUCCESS
    assert (fake_skills.store / "alpha" / "SKILL.md").exists()
    assert (fake_skills.store / "beta" / "SKILL.md").exists()
    out = capsys.readouterr().out
    assert "2" in out and "skill" in out.lower()


def test_list_skills_shows_store(fake_skills, capsys) -> None:
    cmd_import(SimpleNamespace(source="claude", skills=True))
    rc = cmd_list(SimpleNamespace(skills=True))
    assert rc == EXIT_SUCCESS
    out = capsys.readouterr().out
    assert "alpha" in out and "beta" in out


def test_port_skills_writes_to_target(fake_skills) -> None:
    cmd_import(SimpleNamespace(source="claude", skills=True))
    args = SimpleNamespace(source="claude", to="opencode", kind="skills", dry_run=False, yes=True)
    rc = cmd_port(args)
    assert rc in (EXIT_SUCCESS, 1)  # 1 if drop-key warnings
    assert (fake_skills.opencode / "alpha" / "SKILL.md").exists()
    # opencode drops `model` -> should not be in the written file
    written = (fake_skills.opencode / "alpha" / "SKILL.md").read_text()
    assert "model:" not in written


def test_port_skills_dry_run_writes_nothing(fake_skills) -> None:
    cmd_import(SimpleNamespace(source="claude", skills=True))
    args = SimpleNamespace(source="claude", to="opencode", kind="skills", dry_run=True, yes=True)
    rc = cmd_port(args)
    assert rc in (EXIT_SUCCESS, 1)
    assert not fake_skills.opencode.exists()


def test_port_mcp_default_kind_unaffected(fake_skills) -> None:
    """Without --kind skills, port still does MCP (default), not skills."""
    # No manifest servers, but the path must still be the MCP path (no skills written).
    fake_skills.manifest.write_text(json.dumps({"mcpx": {"version": "2.0"}, "servers": {}}))
    args = SimpleNamespace(source="claude", to="opencode", kind="mcp", dry_run=True, yes=True)
    rc = cmd_port(args)
    assert rc == EXIT_SUCCESS
    assert not fake_skills.opencode.exists()


def test_list_skills_empty_store_errors(fake_skills) -> None:
    rc = cmd_list(SimpleNamespace(skills=True))
    assert rc == EXIT_CONFIG_ERROR
