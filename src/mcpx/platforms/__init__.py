# Platform adapter registry
from mcpx.models import PlatformAdapter
from mcpx.platforms.claude import ClaudeAdapter
from mcpx.platforms.cline import ClineAdapter
from mcpx.platforms.codex import CodexAdapter
from mcpx.platforms.gemini import GeminiAdapter
from mcpx.platforms.kilo import KiloAdapter
from mcpx.platforms.roo import RooAdapter

# Registry of all available platform adapters
ALL_PLATFORMS: list[type[PlatformAdapter]] = [
    ClaudeAdapter,
    GeminiAdapter,
    CodexAdapter,
    ClineAdapter,
    RooAdapter,
    KiloAdapter,
]

__all__ = [
    "PlatformAdapter",
    "ClaudeAdapter",
    "GeminiAdapter",
    "CodexAdapter",
    "ClineAdapter",
    "RooAdapter",
    "KiloAdapter",
    "ALL_PLATFORMS",
    "get_all_platforms",
]


def get_all_platforms() -> list[PlatformAdapter]:
    """Instantiate and return all platform adapters.

    ABOUTME: Creates instances of all registered adapters
    ABOUTME: Returns list for easy iteration
    """
    return [platform_cls() for platform_cls in ALL_PLATFORMS]
