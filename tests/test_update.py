# ABOUTME: Tests for `mcpx update` — upgrades installed CLI tools via declarative per-tool recipes.
# ABOUTME: Written test-first. Runs each tool's update command; notes guidance for non-CLI tools.
from types import SimpleNamespace
from unittest.mock import patch

from mcpx.cli import EXIT_SUCCESS, cmd_update
from mcpx.descriptors import REGISTRY
from mcpx.update import UpdateRecipe, run_updates


def test_every_descriptor_has_an_update_recipe() -> None:
    """Each tool declares how it updates (a command) or why it can't (a note)."""
    for tool_id, desc in REGISTRY.items():
        assert desc.update is not None, f"{tool_id} has no update recipe"
        assert desc.update.command is not None or desc.update.note is not None


def test_self_updating_clis_have_commands() -> None:
    assert REGISTRY["codex"].update.command == ["codex", "update"]
    assert REGISTRY["claude"].update.command == ["claude", "update"]
    assert REGISTRY["opencode"].update.command == ["opencode", "upgrade"]


def test_gemini_uses_npm() -> None:
    cmd = REGISTRY["gemini"].update.command
    assert cmd is not None
    assert cmd[:3] == ["npm", "install", "-g"]


def test_vscode_extensions_have_note_not_command() -> None:
    for tool_id in ("cline", "kilo"):
        recipe = REGISTRY[tool_id].update
        assert recipe.command is None
        assert recipe.note and "VS Code" in recipe.note


def test_run_updates_runs_command_when_tool_installed() -> None:
    desc = SimpleNamespace(
        id="codex", display_name="Codex CLI",
        update=UpdateRecipe(command=["codex", "update"]),
    )
    calls = []

    def fake_run(cmd):
        calls.append(cmd)
        return 0  # success

    with patch("mcpx.update.shutil.which", return_value="/usr/bin/codex"):
        results = run_updates([desc], runner=fake_run)

    assert calls == [["codex", "update"]]
    assert results[0].ran is True
    assert results[0].ok is True


def test_run_updates_skips_uninstalled_tool() -> None:
    desc = SimpleNamespace(
        id="codex", display_name="Codex CLI",
        update=UpdateRecipe(command=["codex", "update"]),
    )
    with patch("mcpx.update.shutil.which", return_value=None):
        results = run_updates([desc], runner=lambda c: 0)
    assert results[0].ran is False
    assert "not installed" in results[0].message.lower()


def test_run_updates_reports_command_failure() -> None:
    desc = SimpleNamespace(
        id="opencode", display_name="OpenCode",
        update=UpdateRecipe(command=["opencode", "upgrade"]),
    )
    with patch("mcpx.update.shutil.which", return_value="/usr/bin/opencode"):
        results = run_updates([desc], runner=lambda c: 1)  # non-zero exit
    assert results[0].ran is True
    assert results[0].ok is False


def test_run_updates_emits_note_for_non_cli_tool() -> None:
    desc = SimpleNamespace(
        id="cline", display_name="Cline",
        update=UpdateRecipe(command=None, note="Update via VS Code Extensions panel."),
    )
    results = run_updates([desc], runner=lambda c: 0)
    assert results[0].ran is False
    assert "VS Code" in results[0].message


def test_cmd_update_returns_success(capsys) -> None:
    """The CLI command runs without error and prints a summary."""
    args = SimpleNamespace()
    with patch("mcpx.cli.run_updates") as mock_run:
        mock_run.return_value = []
        rc = cmd_update(args)
    assert rc == EXIT_SUCCESS
