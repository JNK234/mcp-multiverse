# ABOUTME: Generic skills import/export engine — parallels mcp_engine, driven by descriptor data.
# ABOUTME: import_skills (tool -> SkillIR) and export_skills (SkillIR -> tool's skills dir).
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mcpx.codecs.skill_dir import read_skill, write_skill
from mcpx.engine.mcp_engine import resolve_path
from mcpx.ir import SkillIR
from mcpx.utils.backup import create_backup, get_backup_dir

if TYPE_CHECKING:
    from mcpx.descriptors.types import ToolDescriptor


@dataclass
class SkillsExportResult:
    """Outcome of exporting skills to one tool.

    ABOUTME: written = skill names written (or that would be, on dry-run).
    ABOUTME: warnings = lossy notes (dropped frontmatter keys) sourced from descriptor data.
    """

    tool_id: str
    path: Path
    written: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def import_skills(desc: ToolDescriptor) -> dict[str, SkillIR]:
    """Read a tool's skills directory into canonical SkillIRs.

    ABOUTME: Returns {} if the tool declares no skills dir or the dir is absent.
    ABOUTME: Only directories containing a SKILL.md are treated as skills.
    """
    if "skills" not in desc.config_paths:
        return {}
    skills_dir = resolve_path(desc, "skills")
    if not skills_dir.exists():
        return {}

    skills: dict[str, SkillIR] = {}
    for child in sorted(skills_dir.iterdir()):
        if not child.is_dir():
            continue
        # Resolve symlinked skill dirs; require a SKILL.md to count as a skill.
        if not (child.resolve() / "SKILL.md").exists():
            continue
        skill = read_skill(child)
        skills[skill.name] = skill
    return skills


def export_skills(
    desc: ToolDescriptor,
    skills: dict[str, SkillIR],
    *,
    dry_run: bool = False,
) -> SkillsExportResult:
    """Write each SkillIR into the tool's skills dir, dropping unsupported frontmatter keys.

    ABOUTME: Backs up an existing skill dir (labeled by tool id) before overwriting.
    ABOUTME: drop_frontmatter_keys comes from the descriptor's SkillsSpec (data, not branches).
    """
    skills_root = resolve_path(desc, "skills")
    result = SkillsExportResult(tool_id=desc.id, path=skills_root)

    if desc.skills is None or "skills" not in desc.config_paths:
        result.warnings.append(f"{desc.display_name}: no skills support — skipped")
        return result

    drop_keys = tuple(desc.skills.drop_frontmatter_keys)

    for name, skill in skills.items():
        result.written.append(name)
        if dry_run:
            # Still surface drop-key warnings on dry-run (preview lossiness).
            for key in drop_keys:
                if key in skill.frontmatter:
                    result.warnings.append(
                        f"skill '{name}': would drop frontmatter key(s) "
                        f"{', '.join(k for k in drop_keys if k in skill.frontmatter)} "
                        f"(not supported by {desc.display_name})"
                    )
                    break
            continue

        out_dir = skills_root / name
        if out_dir.exists():
            _backup_skill_dir(out_dir, desc.id)
        warnings = write_skill(out_dir, skill, drop_keys=drop_keys)
        result.warnings.extend(warnings)

    return result


def _backup_skill_dir(skill_dir: Path, tool_id: str) -> None:
    """Back up an existing skill's SKILL.md before overwrite (best-effort, reuses backup util)."""
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        create_backup(skill_md, get_backup_dir(), label=f"{tool_id}-skill-{skill_dir.name}")
