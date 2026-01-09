# Core data models for mcpx
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable, Literal


@dataclass(frozen=True)
class MCPServer:
    """Immutable MCP server configuration.

    ABOUTME: Uses frozen dataclass to prevent accidental mutation
    ABOUTME: Only includes fields portable across all platforms
    ABOUTME: Supports both stdio and HTTP server types
    """
    name: str
    type: Literal["stdio", "http"]
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class Config:
    """mcpx configuration loaded from config.json.

    ABOUTME: Contains version and dict of named MCP servers
    ABOUTME: Servers dict uses name as key for easy lookup
    """
    version: str
    servers: dict[str, MCPServer]


@runtime_checkable
class PlatformAdapter(Protocol):
    """Protocol for platform-specific config adapters.

    ABOUTME: Defines interface all platform adapters must implement
    ABOUTME: Uses @runtime_checkable for isinstance() support
    """

    @property
    def name(self) -> str:
        """Human-readable platform name."""
        ...

    @property
    def config_path(self) -> Path | None:
        """Path to platform config file, or None if not found."""
        ...

    def load(self) -> dict[str, MCPServer]:
        """Load existing MCP servers from platform config."""
        ...

    def save(self, servers: dict[str, MCPServer]) -> None:
        """Save MCP servers to platform config."""
        ...

    def save_project(self, servers: dict[str, MCPServer], project_dir: Path) -> None:
        """Save MCP servers to project-level config.

        ABOUTME: Optional method for platforms with project-level support
        ABOUTME: Raises NotImplementedError if not supported
        """
        ...
