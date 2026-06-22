# ABOUTME: Canonical intermediate representation (IR) — the hub every tool maps to/from.
# ABOUTME: MCPServerIR is the tool-agnostic superset of every tool's MCP server fields.
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Transport(str, Enum):
    """MCP server transport. The canonical, tool-agnostic vocabulary.

    ABOUTME: stdio = local command process; http = remote URL (streamable_http/sse umbrella).
    ABOUTME: Each tool descriptor maps this to its own native vocab (local/remote, etc.).
    """

    STDIO = "stdio"
    HTTP = "http"


@dataclass
class MCPServerIR:
    """Canonical MCP server — superset of every tool's fields.

    ABOUTME: The single source-of-truth shape for one MCP server in the IR hub.
    ABOUTME: `extra` (namespaced by source-tool id) preserves native fields no IR field maps to.

    Secrets: env/headers values keep ${VAR} references verbatim. The port path never
    expands them to literals (that would scatter plaintext secrets across config files).
    """

    name: str
    transport: Transport
    # stdio
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    # http
    url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    bearer_token_env_var: str | None = None
    # cross-cutting
    disabled: bool = False
    auto_approve: list[str] = field(default_factory=list)
    # lossless escape hatch: native fields with no IR home, keyed by source-tool id
    # e.g. extra = {"cline": {"timeout": 60}, "codex": {"startup_timeout_ms": 10000}}
    extra: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class Manifest:
    """The persisted IR hub (`~/.mcpx/manifest.json`).

    ABOUTME: Authoritative server set imported from the source tool (Claude Code).
    ABOUTME: artifacts (skills/commands/agents) reserved for a later cut — not used yet.
    """

    version: str
    servers: dict[str, MCPServerIR] = field(default_factory=dict)
