# ABOUTME: Tests that each descriptor declares its skills dir + drop-keys (data, not branches).
# ABOUTME: Claude is the source; targets drop allowed-tools/model except Gemini/Kilo (full spec).
from mcpx.descriptors import REGISTRY


def test_every_tool_has_a_skills_dir() -> None:
    for tool_id, desc in REGISTRY.items():
        assert "skills" in desc.config_paths, f"{tool_id} missing config_paths['skills']"


def test_claude_skills_dir_is_source() -> None:
    assert REGISTRY["claude"].config_paths["skills"] == "~/.claude/skills"


def test_target_skills_dirs() -> None:
    assert REGISTRY["codex"].config_paths["skills"] == "~/.codex/skills"
    assert REGISTRY["opencode"].config_paths["skills"] == "~/.config/opencode/skills"
    assert REGISTRY["gemini"].config_paths["skills"] == "~/.gemini/skills"
    assert REGISTRY["cline"].config_paths["skills"] == "~/.cline/skills"
    assert REGISTRY["kilo"].config_paths["skills"] == "~/.kilo/skills"


def test_every_tool_has_skills_spec() -> None:
    for tool_id, desc in REGISTRY.items():
        assert desc.skills is not None, f"{tool_id} has no SkillsSpec"


def test_gemini_and_kilo_drop_nothing() -> None:
    assert REGISTRY["gemini"].skills.drop_frontmatter_keys == ()
    assert REGISTRY["kilo"].skills.drop_frontmatter_keys == ()


def test_codex_opencode_cline_drop_allowed_tools_and_model() -> None:
    for tool_id in ("codex", "opencode", "cline"):
        keys = REGISTRY[tool_id].skills.drop_frontmatter_keys
        assert "allowed-tools" in keys
        assert "model" in keys
