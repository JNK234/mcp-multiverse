# ABOUTME: skill_dir codec — read/write a skill directory (SKILL.md + helper files).
# ABOUTME: Ignore policy skips deps/junk by pattern (no skill names); helper files byte-exact.
from __future__ import annotations

import fnmatch
from pathlib import Path

from mcpx.codecs.frontmatter import join, split
from mcpx.ir import SkillIR

# Junk/dependency patterns to skip when copying a skill — matched against any path component
# (dir name) or the file name. Generic by design: no skill-specific names anywhere.
IGNORE_DIR_NAMES = {"node_modules", ".git", "__pycache__", ".venv", "venv"}
IGNORE_FILE_GLOBS = (
    "*.lock",
    "package-lock.json",
    "bun.lock",
    ".temp-execution-*",
    ".DS_Store",
    "*.pyc",
)


def _is_ignored(rel: Path) -> bool:
    """True if a relative path falls under the ignore policy (junk/deps)."""
    if any(part in IGNORE_DIR_NAMES for part in rel.parts):
        return True
    name = rel.name
    return any(fnmatch.fnmatch(name, pat) for pat in IGNORE_FILE_GLOBS)


def read_skill(skill_dir: Path) -> SkillIR:
    """Read a skill directory into a SkillIR.

    ABOUTME: Resolves symlinked skill dirs (reads the target); name comes from the link dir.
    ABOUTME: Collects every non-ignored file except SKILL.md into files (relpath -> bytes).
    """
    name = skill_dir.name
    root = skill_dir.resolve()  # follow symlinks to the real dir

    skill_md = root / "SKILL.md"
    if skill_md.exists():
        frontmatter, body = split(skill_md.read_text(encoding="utf-8"))
    else:
        frontmatter, body = {}, ""

    files: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if rel.name == "SKILL.md" and rel.parent == Path("."):
            continue  # SKILL.md is carried as frontmatter+body, not a helper file
        if _is_ignored(rel):
            continue
        files[rel.as_posix()] = path.read_bytes()

    return SkillIR(name=name, frontmatter=frontmatter, body=body, files=files)


def write_skill(out_dir: Path, skill: SkillIR, drop_keys: tuple[str, ...]) -> list[str]:
    """Write a SkillIR into out_dir (SKILL.md + helper files). Returns warnings.

    ABOUTME: Drops frontmatter keys the target tool can't represent (warns once, naming them).
    ABOUTME: Helper files are written byte-exact, recreating subdirectories.
    """
    warnings: list[str] = []

    frontmatter = dict(skill.frontmatter)
    dropped = [k for k in drop_keys if k in frontmatter]
    for key in dropped:
        del frontmatter[key]
    if dropped:
        warnings.append(
            f"skill '{skill.name}': dropped frontmatter key(s) {', '.join(dropped)} "
            f"(not supported by this tool)"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "SKILL.md").write_text(join(frontmatter, skill.body), encoding="utf-8")

    for rel, data in skill.files.items():
        dest = out_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)

    return warnings
