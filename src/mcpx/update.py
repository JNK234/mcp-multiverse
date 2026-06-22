# ABOUTME: `mcpx update` engine — upgrades installed CLI tools via declarative per-tool recipes.
# ABOUTME: Runs each tool's update command if its binary is installed; notes guidance otherwise.
from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcpx.descriptors.types import ToolDescriptor


@dataclass(frozen=True)
class UpdateRecipe:
    """How one tool updates itself — declarative, lives on the descriptor.

    ABOUTME: command is the argv to run (e.g. ['codex','update']) or None if the tool
    ABOUTME: can't be updated from a shell (VS Code extensions). note is shown when there's
    ABOUTME: no command, telling the user how to update it manually.
    """

    command: list[str] | None = None
    note: str | None = None


@dataclass
class UpdateResult:
    """Outcome of attempting to update one tool."""

    tool_id: str
    display_name: str
    ran: bool
    ok: bool = False
    message: str = ""


def _default_runner(cmd: list[str]) -> int:
    """Run an update command, streaming its output; return the exit code."""
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


def run_updates(
    descriptors: list[ToolDescriptor],
    *,
    runner: Callable[[list[str]], int] = _default_runner,
) -> list[UpdateResult]:
    """Update each tool that has a runnable update command and whose binary is installed.

    ABOUTME: A tool with no command emits its note (ran=False). A tool whose first command
    ABOUTME: word isn't on PATH is skipped as 'not installed'. runner is injectable for tests.
    """
    results: list[UpdateResult] = []
    for desc in descriptors:
        recipe = desc.update
        if recipe is None or recipe.command is None:
            note = recipe.note if recipe else None
            results.append(UpdateResult(
                tool_id=desc.id, display_name=desc.display_name, ran=False,
                message=note or "No update method available.",
            ))
            continue

        binary = recipe.command[0]
        if shutil.which(binary) is None:
            results.append(UpdateResult(
                tool_id=desc.id, display_name=desc.display_name, ran=False,
                message=f"{binary} not installed — skipped.",
            ))
            continue

        code = runner(recipe.command)
        results.append(UpdateResult(
            tool_id=desc.id, display_name=desc.display_name, ran=True,
            ok=(code == 0),
            message="updated" if code == 0 else f"update failed (exit {code})",
        ))
    return results
