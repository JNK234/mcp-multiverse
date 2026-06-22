# ABOUTME: Tests for the skill_dir codec — read/write a skill directory (SKILL.md + helper files).
# ABOUTME: Written test-first. Ignore policy skips junk; helper files byte-exact; drop-keys warns.
from pathlib import Path

from mcpx.codecs.skill_dir import read_skill, write_skill
from mcpx.ir import SkillIR


def _make_skill(dir_: Path, *, with_junk: bool = False) -> None:
    dir_.mkdir(parents=True)
    (dir_ / "SKILL.md").write_text(
        "---\nname: demo\ndescription: A demo\n"
        "allowed-tools:\n  - Bash\nmodel: opus\n---\nBody text.\n"
    )
    (dir_ / "scripts").mkdir()
    (dir_ / "scripts" / "run.sh").write_text("#!/bin/sh\necho hi\n")
    (dir_ / "references").mkdir()
    (dir_ / "references" / "data.csv").write_bytes(b"a,b\n1,2\n")
    if with_junk:
        (dir_ / "node_modules").mkdir()
        (dir_ / "node_modules" / "pkg.js").write_text("junk")
        (dir_ / "package-lock.json").write_text("{}")
        (dir_ / ".temp-execution-123.js").write_text("temp")
        (dir_ / ".DS_Store").write_bytes(b"\x00")


def test_read_skill_basic(tmp_path: Path) -> None:
    _make_skill(tmp_path / "demo")
    skill = read_skill(tmp_path / "demo")
    assert skill.name == "demo"
    assert skill.frontmatter["name"] == "demo"
    assert skill.frontmatter["allowed-tools"] == ["Bash"]
    assert skill.body == "Body text.\n"


def test_read_skill_collects_helper_files_byte_exact(tmp_path: Path) -> None:
    _make_skill(tmp_path / "demo")
    skill = read_skill(tmp_path / "demo")
    assert "scripts/run.sh" in skill.files
    assert skill.files["scripts/run.sh"] == b"#!/bin/sh\necho hi\n"
    assert skill.files["references/data.csv"] == b"a,b\n1,2\n"
    # SKILL.md is NOT in files (it's frontmatter+body)
    assert "SKILL.md" not in skill.files


def test_read_skill_ignores_junk(tmp_path: Path) -> None:
    _make_skill(tmp_path / "demo", with_junk=True)
    skill = read_skill(tmp_path / "demo")
    paths = set(skill.files)
    assert not any("node_modules" in p for p in paths)
    assert "package-lock.json" not in paths
    assert not any(p.startswith(".temp-execution-") for p in paths)
    assert ".DS_Store" not in paths
    # real helper files still present
    assert "scripts/run.sh" in paths


def test_read_skill_resolves_symlink(tmp_path: Path) -> None:
    real = tmp_path / "real-skill"
    _make_skill(real)
    link = tmp_path / "linked"
    link.symlink_to(real, target_is_directory=True)
    skill = read_skill(link)
    assert skill.name == "linked"  # name from the link dir
    assert skill.body == "Body text.\n"
    assert "scripts/run.sh" in skill.files


def test_write_skill_roundtrip(tmp_path: Path) -> None:
    _make_skill(tmp_path / "demo")
    skill = read_skill(tmp_path / "demo")
    out = tmp_path / "out" / "demo"
    warnings = write_skill(out, skill, drop_keys=())
    assert (out / "SKILL.md").exists()
    assert (out / "scripts" / "run.sh").read_bytes() == b"#!/bin/sh\necho hi\n"
    assert (out / "references" / "data.csv").read_bytes() == b"a,b\n1,2\n"
    assert warnings == []


def test_write_skill_drops_keys_and_warns(tmp_path: Path) -> None:
    _make_skill(tmp_path / "demo")
    skill = read_skill(tmp_path / "demo")
    out = tmp_path / "out" / "demo"
    warnings = write_skill(out, skill, drop_keys=("allowed-tools", "model"))
    written = (out / "SKILL.md").read_text()
    assert "allowed-tools" not in written
    assert "model:" not in written
    assert "name: demo" in written  # kept keys survive
    # one warning naming the dropped keys
    assert any("allowed-tools" in w and "model" in w for w in warnings)


def test_write_skill_no_drop_keeps_everything(tmp_path: Path) -> None:
    _make_skill(tmp_path / "demo")
    skill = read_skill(tmp_path / "demo")
    out = tmp_path / "out" / "demo"
    write_skill(out, skill, drop_keys=())
    written = (out / "SKILL.md").read_text()
    assert "allowed-tools" in written
    assert "model: opus" in written


def test_skillir_dataclass_fields() -> None:
    s = SkillIR(name="x", frontmatter={"name": "x"}, body="b", files={"a.txt": b"y"})
    assert s.name == "x"
    assert s.files["a.txt"] == b"y"
