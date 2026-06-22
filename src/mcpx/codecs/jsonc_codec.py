# ABOUTME: JSONC codec for .jsonc files (OpenCode's opencode.jsonc) with // and /* */ comments.
# ABOUTME: Strips comments on read; writes valid JSON. Foreign keys ($schema) survive on rewrite.
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast

# Match // line comments and /* block comments, but NOT those inside strings.
# We scan char-by-char honoring string state to avoid corrupting URLs like "https://...".
_STRING_OR_COMMENT = re.compile(
    r'"(?:\\.|[^"\\])*"'      # a JSON string (handles escaped quotes)
    r"|//[^\n]*"             # line comment
    r"|/\*.*?\*/",           # block comment
    re.DOTALL,
)


def _strip_comments(text: str) -> str:
    """Remove // and /* */ comments while leaving string contents intact.

    ABOUTME: Replaces comment spans with empty; leaves string literals (incl. //) untouched.
    """

    def repl(m: re.Match[str]) -> str:
        token = m.group(0)
        # If it's a string literal, keep it verbatim; otherwise it's a comment -> drop.
        return token if token.startswith('"') else ""

    return _STRING_OR_COMMENT.sub(repl, text)


def _strip_trailing_commas(text: str) -> str:
    """Remove trailing commas before } or ] (JSONC allows them, strict JSON doesn't)."""
    return re.sub(r",(\s*[}\]])", r"\1", text)


class JsoncCodec:
    """Reads/writes JSONC files (comments tolerated on read)."""

    def read(self, path: Path) -> dict[str, Any]:
        """Return parsed JSONC (comments/trailing commas stripped), or {} if missing.

        ABOUTME: Raises ValueError on malformed content with the offending path.
        """
        if not path.exists():
            return {}
        raw = path.read_text(encoding="utf-8")
        cleaned = _strip_trailing_commas(_strip_comments(raw))
        if not cleaned.strip():
            return {}
        try:
            return cast(dict[str, Any], json.loads(cleaned))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSONC in {path}: {e}") from e

    def write(self, path: Path, data: dict[str, Any]) -> None:
        """Write data as JSON (valid JSONC) with 2-space indent and trailing newline.

        ABOUTME: Comments in the original file are not reconstructed; data keys are preserved.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
