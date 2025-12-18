#!/usr/bin/env python3
"""
ABOUTME: MCP Configuration Path Verifier
ABOUTME: Verifies that our sync manager uses official MCP configuration paths
"""

import os
import platform
from pathlib import Path
from typing import Dict, Any
import sys

# Official MCP configuration paths from documentation
OFFICIAL_PATHS = {
    "Windows": {
        "claude_user": "{APPDATA}/Claude/claude_desktop_config.json",
        "claude_project": "./.mcp.json",
        "gemini": "{APPDATA}/gemini/settings.json",
        "cline": "{APPDATA}/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json",
        "roo": "{APPDATA}/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json",
    },
    "Darwin": {  # macOS
        "claude_user": "~/.claude/claude_desktop_config.json",
        "claude_project": "./.mcp.json",
        "gemini": "~/.gemini/settings.json",
        "cline": "~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json",
        "roo": "~/Library/Application Support/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json",
    },
    "Linux": {
        "claude_user": "~/.claude/claude_desktop_config.json",
        "claude_project": "./.mcp.json",
        "gemini": "~/.gemini/settings.json",
        "cline": "~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json",
        "roo": "~/.config/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json",
    }
}

def expand_path(path_str: str) -> Path:
    """Expand variables in path string"""
    path_str = path_str.replace("{APPDATA}", os.environ.get("APPDATA", ""))
    path_str = path_str.replace("{HOME}", os.environ.get("HOME", ""))
    return Path(path_str).expanduser()

def verify_against_official():
    """Verify our paths match official documentation"""

    # Import our sync manager to get the paths
    sys.path.insert(0, str(Path(__file__).parent))
    # Import using importlib since filename has hyphens
    import importlib.util
    spec = importlib.util.spec_from_file_location("mcp_sync_manager", str(Path(__file__).parent / "mcp-sync-manager.py"))
    mcp_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mcp_module)
    Platforms = mcp_module.Platforms

    our_platforms = Platforms()
    current_os = platform.system()
    print(f"✓ Verifying paths on {current_os}\n")

    # Get official paths for this OS
    official_paths = OFFICIAL_PATHS.get(current_os, OFFICIAL_PATHS["Linux"])

    # Check Claude paths
    print("📋 Claude Code:")
    print(f"   Official user config: {official_paths['claude_user']}")
    print(f"   Our implementation:   {our_platforms.claude_user_config}")
    official_claude = expand_path(official_paths['claude_user'])
    if our_platforms.claude_user_config.resolve() == official_claude.resolve():
        print("   ✅ MATCH\n")
    else:
        print("   ❌ MISMATCH\n")
        print(f"   Expected: {official_claude}")
        print(f"   Got:      {our_platforms.claude_user_config}")

    # Check Gemini
    print("📋 Gemini CLI:")
    print(f"   Official:           {official_paths['gemini']}")
    print(f"   Our implementation: {our_platforms.gemini_config}")
    official_gemini = expand_path(official_paths['gemini'])
    if our_platforms.gemini_config.resolve() == official_gemini.resolve():
        print("   ✅ MATCH\n")
    else:
        print("   ❌ MISMATCH\n")
        print(f"   Expected: {official_gemini}")
        print(f"   Got:      {our_platforms.gemini_config}")

    # Check Cline
    print("📋 Cline:")
    print(f"   Official:           {official_paths['cline']}")
    print(f"   Our implementation: {our_platforms.cline_config}")
    official_cline = expand_path(official_paths['cline'])
    if our_platforms.cline_config.resolve() == official_cline.resolve():
        print("   ✅ MATCH\n")
    else:
        print("   ❌ MISMATCH\n")
        print(f"   Expected: {official_cline}")
        print(f"   Got:      {our_platforms.cline_config}")

    # Check Roo
    print("📋 Roo Code:")
    print(f"   Official:           {official_paths['roo']}")
    print(f"   Our implementation: {our_platforms.roo_config}")
    official_roo = expand_path(official_paths['roo'])
    if our_platforms.roo_config.resolve() == official_roo.resolve():
        print("   ✅ MATCH\n")
    else:
        print("   ❌ MISMATCH\n")
        print(f"   Expected: {official_roo}")
        print(f"   Got:      {our_platforms.roo_config}")

    # Check if files actually exist
    print("\n🔍 Checking if config files exist on this system:")
    for name, path in [("Claude", our_platforms.claude_user_config),
                       ("Gemini", our_platforms.gemini_config),
                       ("Cline", our_platforms.cline_config),
                       ("Roo", our_platforms.roo_config)]:
        status = "✅ EXISTS" if path.exists() else "❌ NOT FOUND"
        print(f"   {name:12} {path.name:30} {status}")

if __name__ == "__main__":
    verify_against_official()
