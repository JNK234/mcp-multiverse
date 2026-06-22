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

    frontmatter = _parse_yaml_lenient(yaml_text)
    return frontmatter, body


def _parse_yaml_lenient(yaml_text: str) -> dict[str, Any]:
    """Parse frontmatter YAML, falling back to a line-based parse on strict-YAML errors.

    ABOUTME: Claude SKILL.md frontmatter often has unquoted values containing ': '
    ABOUTME: (e.g. description with "Research: X") that strict YAML rejects. Rather than
    ABOUTME: crash, treat each top-level 'key: value' line as a string value.
    """
    if not yaml_text.strip():
        return {}
    try:
        parsed = yaml.safe_load(yaml_text)
        if isinstance(parsed, dict):
            return parsed
    except yaml.YAMLError:
        pass

    # Lenient fallback: split each top-level 'key: value' line; everything after the first
    # ': ' is a literal string value. Continuation/indented lines append to the prior value.
    result: dict[str, Any] = {}
    last_key: str | None = None
    for raw in yaml_text.splitlines():
        if not raw.strip():
            continue
        if raw[:1] in (" ", "\t") and last_key is not None:
            result[last_key] = f"{result[last_key]} {raw.strip()}".strip()
            continue
        if ": " in raw:
            key, value = raw.split(": ", 1)
            result[key.strip()] = value.strip()
            last_key = key.strip()
        elif raw.endswith(":"):
            key = raw[:-1].strip()
            result[key] = ""
            last_key = key
    return result


def join(frontmatter: dict[str, Any], body: str) -> str:
    """Render a frontmatter dict + body back into '---\\nYAML\\n---\\nbody' text.

    ABOUTME: With an empty frontmatter dict, returns the body unchanged (no fence).
    ABOUTME: Keys are emitted in insertion order (sort_keys=False) for idempotency.
    """
    if not frontmatter:
        return body
    yaml_text = yaml.safe_dump(frontmatter, sort_keys=False, default_flow_style=False)
    return f"---\n{yaml_text}---\n{body}"
