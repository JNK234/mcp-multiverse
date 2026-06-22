# ABOUTME: Frontmatter codec — split/join '---\nYAML\n---\nbody' for SKILL.md and friends.
# ABOUTME: YAML frontmatter is parsed; the body after it is kept byte-exact (never re-serialized).
from __future__ import annotations

from typing import Any

import yaml


def split(text: str) -> tuple[dict[str, Any], str]:
    """Split frontmatter text into (frontmatter dict, body).

    ABOUTME: Returns ({}, text) when there is no leading '---' frontmatter block.
    ABOUTME: The body (everything after the closing '---' line) is returned byte-exact.
    """
    if not text.startswith("---\n") and text != "---\n" and not text.startswith("---\r\n"):
        return {}, text

    # Find the closing fence. The opening '---' is the first line; look for the next '---'
    # on its own line.
    lines = text.splitlines(keepends=True)
    # lines[0] is the opening '---'. Find the next line that is exactly '---'.
    close_idx = None
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") == "---":
            close_idx = i
            break

    if close_idx is None:
        # Malformed (no closing fence) — treat the whole thing as body.
        return {}, text

    yaml_text = "".join(lines[1:close_idx])
    body = "".join(lines[close_idx + 1:])

    parsed = yaml.safe_load(yaml_text) if yaml_text.strip() else {}
    frontmatter: dict[str, Any] = parsed if isinstance(parsed, dict) else {}
    return frontmatter, body


def join(frontmatter: dict[str, Any], body: str) -> str:
    """Render a frontmatter dict + body back into '---\\nYAML\\n---\\nbody' text.

    ABOUTME: With an empty frontmatter dict, returns the body unchanged (no fence).
    ABOUTME: Keys are emitted in insertion order (sort_keys=False) for idempotency.
    """
    if not frontmatter:
        return body
    yaml_text = yaml.safe_dump(frontmatter, sort_keys=False, default_flow_style=False)
    return f"---\n{yaml_text}---\n{body}"
