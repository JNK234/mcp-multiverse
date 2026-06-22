# ABOUTME: Codec protocol and format->codec registry.
# ABOUTME: A codec reads a whole config file into a dict and writes a dict back.
from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class Codec(Protocol):
    """Reads/writes a whole config file as a structured dict.

    ABOUTME: read() returns {} for a missing file; write() creates parent dirs.
    ABOUTME: Codecs are format-specific (json/jsonc/toml) and tool-agnostic.
    """

    def read(self, path: Path) -> dict[str, Any]:
        """Parse the file at path into a dict. Returns {} if the file is missing."""
        ...

    def write(self, path: Path, data: dict[str, Any]) -> None:
        """Serialize data to the file at path, creating parent directories."""
        ...


def codec_for(fmt: str) -> Codec:
    """Return the codec for a format id.

    ABOUTME: Lazy imports avoid a circular import between codecs at module load.
    ABOUTME: Raises ValueError for an unknown format.
    """
    if fmt in ("json",):
        from mcpx.codecs.json_codec import JsonCodec

        return JsonCodec()
    if fmt in ("jsonc",):
        from mcpx.codecs.jsonc_codec import JsoncCodec

        return JsoncCodec()
    if fmt in ("toml-flat", "toml"):
        from mcpx.codecs.toml_codec import TomlCodec

        return TomlCodec()
    raise ValueError(f"No codec registered for format '{fmt}'")
