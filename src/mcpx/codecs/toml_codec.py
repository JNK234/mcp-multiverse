# ABOUTME: TOML codec for Codex config.toml — reads via tomli, writes [mcp_servers.<name>] tables.
# ABOUTME: Supports stdio (command/args/env) and http (url/http_headers/bearer) servers.
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import tomli


class TomlCodec:
    """Reads/writes Codex TOML config, managing only the mcp_servers section.

    ABOUTME: read() returns the whole parsed file; write() splices the [mcp_servers.*]
    ABOUTME: tables in place, preserving every other section of the original file byte-for-byte.
    """

    def read(self, path: Path) -> dict[str, Any]:
        """Return the whole parsed TOML file, or {} if missing.

        ABOUTME: Raises ValueError on malformed TOML with the offending path.
        """
        if not path.exists():
            return {}
        try:
            with path.open("rb") as f:
                return tomli.load(f)
        except tomli.TOMLDecodeError as e:
            raise ValueError(f"Invalid TOML in {path}: {e}") from e

    def write(self, path: Path, data: dict[str, Any]) -> None:
        """Write data, rendering data['mcp_servers'] as [mcp_servers.<name>] tables.

        ABOUTME: Preserves all non-mcp_servers content of an existing file verbatim
        ABOUTME: by stripping old [mcp_servers.*] tables and splicing the new block.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        mcp_servers = data.get("mcp_servers", {})
        new_block = _render_mcp_servers(mcp_servers)

        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        preserved = _strip_mcp_servers_tables(existing).rstrip()

        if preserved:
            content = preserved + "\n\n" + new_block if new_block else preserved + "\n"
        else:
            content = new_block if new_block else ""

        if content and not content.endswith("\n"):
            content += "\n"
        path.write_text(content, encoding="utf-8")


def _strip_mcp_servers_tables(text: str) -> str:
    """Remove every [mcp_servers...] table (header + its body) from raw TOML text.

    ABOUTME: A table runs from its [header] line until the next top-level [header] or EOF.
    ABOUTME: Leaves all other tables/top-level keys untouched.
    """
    if not text:
        return ""
    lines = text.splitlines()
    out: list[str] = []
    skipping = False
    header_re = re.compile(r"^\s*\[")
    mcp_header_re = re.compile(r"^\s*\[\[?mcp_servers(\.|\]|\s|$)")
    for line in lines:
        if header_re.match(line):
            skipping = bool(mcp_header_re.match(line))
        if not skipping:
            out.append(line)
    return "\n".join(out)


def _render_mcp_servers(mcp_servers: dict[str, dict[str, Any]]) -> str:
    """Render name->server-dict into [mcp_servers.<name>] TOML tables.

    ABOUTME: stdio servers emit command/args/env; http servers emit url/http_headers/bearer.
    ABOUTME: Unknown extra keys (scalars/arrays/string-maps) are emitted generically.
    """
    blocks: list[str] = []
    for name, cfg in mcp_servers.items():
        lines = [f"[mcp_servers.{name}]"]
        # Stable, readable ordering: known keys first, then any extras.
        ordered_keys = [
            "command", "args", "env", "url", "http_headers",
            "bearer_token_env_var",
        ]
        seen: set[str] = set()
        for key in ordered_keys:
            if key in cfg and not _is_empty(cfg[key]):
                lines.append(_render_kv(key, cfg[key]))
                seen.add(key)
        for extra_key, extra_value in cfg.items():
            if extra_key in seen or _is_empty(extra_value):
                continue
            lines.append(_render_kv(extra_key, extra_value))
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _is_empty(value: Any) -> bool:
    return value is None or value == [] or value == {} or value == ""


def _render_kv(key: str, value: Any) -> str:
    """Render one TOML key = value line for a scalar, array, or inline string-map."""
    if isinstance(value, str):
        return f'{key} = "{_esc(value)}"'
    if isinstance(value, bool):
        return f"{key} = {'true' if value else 'false'}"
    if isinstance(value, int | float):
        return f"{key} = {value}"
    if isinstance(value, list):
        return f"{key} = {_render_array(value)}"
    if isinstance(value, dict):
        return f"{key} = {_render_inline_table(value)}"
    return f'{key} = "{_esc(str(value))}"'


def _render_array(items: list[Any]) -> str:
    parts = []
    for item in items:
        if isinstance(item, str):
            parts.append(f'"{_esc(item)}"')
        elif isinstance(item, bool):
            parts.append("true" if item else "false")
        else:
            parts.append(str(item))
    return "[" + ", ".join(parts) + "]"


def _render_inline_table(data: dict[str, Any]) -> str:
    if not data:
        return "{}"
    pairs = [f'{key} = "{_esc(str(val))}"' for key, val in data.items()]
    return "{ " + ", ".join(pairs) + " }"


def _esc(value: str) -> str:
    """Escape backslashes and double quotes for a TOML basic string."""
    return value.replace("\\", "\\\\").replace('"', '\\"')
