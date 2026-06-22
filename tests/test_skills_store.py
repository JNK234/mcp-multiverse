# ABOUTME: Tests for skills store IO — persist/load SkillIRs under ~/.mcpx/store/skills/.
# ABOUTME: Written test-first. Store keeps skill bodies + helper files byte-exact.
from pathlib import Path

from mcpx.ir import SkillIR
from mcpx.manifest import get_skills_store_dir, load_skills_from_store, save_skills_to_store


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    store = tmp_path / "store" / "skills"
    skills = {
        "alpha": SkillIR(
            name="alpha", frontmatter={"name": "alpha", "description": "d"}, body="Body.\n",
            files={"scripts/run.sh": b"#!/bin/sh\n", "refs/x.md": b"ref\n"},
        ),
        "beta": SkillIR(name="beta", frontmatter={"name": "beta"}, body="B2\n"),
    }
    save_skills_to_store(skills, store)
    loaded = load_skills_from_store(store)
    assert set(loaded) == {"alpha", "beta"}
    assert loaded["alpha"].frontmatter["description"] == "d"
    assert loaded["alpha"].body == "Body.\n"
    assert loaded["alpha"].files["scripts/run.sh"] == b"#!/bin/sh\n"


def test_load_missing_store_returns_empty(tmp_path: Path) -> None:
    assert load_skills_from_store(tmp_path / "nope") == {}


def test_save_replaces_existing(tmp_path: Path) -> None:
    store = tmp_path / "skills"
    save_skills_to_store({"a": SkillIR(name="a", frontmatter={"name": "a"}, body="old\n")}, store)
    save_skills_to_store({"a": SkillIR(name="a", frontmatter={"name": "a"}, body="new\n")}, store)
    loaded = load_skills_from_store(store)
    assert loaded["a"].body == "new\n"


def test_get_skills_store_dir_under_mcpx() -> None:
    d = get_skills_store_dir()
    assert d.name == "skills"
    assert d.parent.name == "store"
    assert ".mcpx" in str(d)
