# ABOUTME: Tests for the skills engine — import skills from a tool, export to targets.
# ABOUTME: Written test-first. Mirrors mcp_engine; store IO under ~/.mcpx/store/skills/.
from pathlib import Path
from types import SimpleNamespace

from mcpx.engine.skills_engine import export_skills, import_skills
from mcpx.ir import SkillIR


def _claude_desc(skills_dir: Path) -> SimpleNamespace:
    return SimpleNamespace(
        id="claude", display_name="Claude Code",
        config_paths={"skills": str(skills_dir)},
        skills=None,
    )


def _target_desc(skills_dir: Path, drop=()) -> SimpleNamespace:
    return SimpleNamespace(
        id="opencode", display_name="OpenCode",
        config_paths={"skills": str(skills_dir)},
        skills=SimpleNamespace(drop_frontmatter_keys=tuple(drop)),
    )


def _seed_skill(root: Path, name: str, body: str = "Body.\n", fm: str = "") -> None:
    d = root / name
    d.mkdir(parents=True)
    front = fm or f"---\nname: {name}\ndescription: d\n---\n"
    (d / "SKILL.md").write_text(front + body)


# --- import -------------------------------------------------------------

def test_import_skills_reads_all_dirs(tmp_path: Path) -> None:
    src = tmp_path / "claude-skills"
    _seed_skill(src, "alpha")
    _seed_skill(src, "beta")
    skills = import_skills(_claude_desc(src))
    assert set(skills) == {"alpha", "beta"}
    assert skills["alpha"].frontmatter["name"] == "alpha"


def test_import_skills_skips_dirs_without_skill_md(tmp_path: Path) -> None:
    src = tmp_path / "claude-skills"
    _seed_skill(src, "good")
    (src / "broken").mkdir()  # no SKILL.md
    skills = import_skills(_claude_desc(src))
    assert set(skills) == {"good"}


def test_import_skills_missing_dir_returns_empty(tmp_path: Path) -> None:
    assert import_skills(_claude_desc(tmp_path / "nope")) == {}


# --- export -------------------------------------------------------------

def test_export_skills_writes_to_target(tmp_path: Path) -> None:
    dest = tmp_path / "opencode-skills"
    skills = {"alpha": SkillIR(name="alpha", frontmatter={"name": "alpha"}, body="B\n")}
    result = export_skills(_target_desc(dest), skills, dry_run=False)
    assert (dest / "alpha" / "SKILL.md").exists()
    assert "alpha" in result.written
    assert result.warnings == []


def test_export_skills_dry_run_writes_nothing(tmp_path: Path) -> None:
    dest = tmp_path / "opencode-skills"
    skills = {"alpha": SkillIR(name="alpha", frontmatter={"name": "alpha"}, body="B\n")}
    result = export_skills(_target_desc(dest), skills, dry_run=True)
    assert not dest.exists()
    assert "alpha" in result.written


def test_export_skills_drops_keys_and_warns(tmp_path: Path) -> None:
    dest = tmp_path / "opencode-skills"
    skills = {
        "alpha": SkillIR(
            name="alpha",
            frontmatter={"name": "alpha", "allowed-tools": ["Bash"], "model": "opus"},
            body="B\n",
        )
    }
    target = _target_desc(dest, drop=("allowed-tools", "model"))
    result = export_skills(target, skills, dry_run=False)
    written = (dest / "alpha" / "SKILL.md").read_text()
    assert "allowed-tools" not in written
    assert "model:" not in written
    assert any("allowed-tools" in w for w in result.warnings)


def test_export_skills_copies_helper_files(tmp_path: Path) -> None:
    dest = tmp_path / "opencode-skills"
    skills = {
        "alpha": SkillIR(
            name="alpha", frontmatter={"name": "alpha"}, body="B\n",
            files={"scripts/run.sh": b"#!/bin/sh\n"},
        )
    }
    export_skills(_target_desc(dest), skills, dry_run=False)
    assert (dest / "alpha" / "scripts" / "run.sh").read_bytes() == b"#!/bin/sh\n"


# --- store round-trip (import real dir -> export elsewhere) -------------

def test_import_then_export_roundtrip(tmp_path: Path) -> None:
    src = tmp_path / "claude-skills"
    d = src / "alpha"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("---\nname: alpha\ndescription: hi\n---\nBody.\n")
    (d / "refs").mkdir()
    (d / "refs" / "x.md").write_text("ref\n")

    skills = import_skills(_claude_desc(src))
    dest = tmp_path / "out"
    export_skills(_target_desc(dest), skills, dry_run=False)

    assert (dest / "alpha" / "SKILL.md").read_text().startswith("---")
    assert (dest / "alpha" / "refs" / "x.md").read_text() == "ref\n"
