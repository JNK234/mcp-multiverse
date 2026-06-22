# ABOUTME: JSON codec for plain .json config files (Claude, Cline, Gemini, Kilo MCP files).
# ABOUTME: Preserves key insertion order (no sort_keys) so re-writes stay idempotent.
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast


class JsonCodec:
    """Reads/writes plain JSON config files."""

    def read(self, path: Path) -> dict[str, Any]:
        """Return parsed JSON, or {} if the file doesn't exist.

        ABOUTME: Raises ValueError on malformed JSON with the offending path.
        """
        if not path.exists():
            return {}
        try:
            with path.open(encoding="utf-8") as f:
                return cast(dict[str, Any], json.load(f))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {path}: {e}") from e

    def write(self, path: Path, data: dict[str, Any]) -> None:
        """Write data as 2-space-indented JSON with a trailing newline.

        ABOUTME: Creates parent dirs; preserves insertion order (no sort_keys).
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
