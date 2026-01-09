# Project-level MCP initialization
import json
import sys
from pathlib import Path

from mcpx.config import get_config_path, load_config
from mcpx.models import MCPServer

# ABOUTME: Terminal codes for interactive UI
CLEAR_SCREEN = "\033[2J\033[H"
BOLD = "\033[1m"
RESET = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"


def interactive_select(items: list[str], preselected: set[str]) -> list[str]:
    """Terminal-based multi-select without external dependencies.

    ABOUTME: Uses arrow keys, space, and enter for selection
    ABOUTME: Pure Python implementation with escape sequences

    Args:
        items: List of items to select from
        preselected: Set of items that should start selected

    Returns:
        List of selected items
    """
    if not items:
        return []

    # Start with preselected items
    selected: set[str] = set(preselected) & set(items)
    current_idx = 0

    try:
        import termios
        import tty

        def getch() -> str:
            """Get a single character from stdin."""
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
                # Handle escape sequences for arrow keys
                if ch == "\x1b":
                    # Read the next two characters
                    ch += sys.stdin.read(2)
                return ch
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

        while True:
            # Clear screen and redraw
            print(CLEAR_SCREEN, end="")
            print(f"{BOLD}Select MCPs to enable for this project:{RESET}")
            print()

            # Display items with current selection state
            for idx, item in enumerate(items):
                prefix = "[x]" if item in selected else "[ ]"
                cursor = f"{CYAN}>>>{RESET} " if idx == current_idx else "    "
                print(f"{cursor}{prefix} {item}")

            print()
            print("Use arrow keys to navigate, space to toggle, enter to confirm.")

            # Get user input
            ch = getch()

            if ch == "\x1b[A":  # Up arrow
                current_idx = (current_idx - 1) % len(items)
            elif ch == "\x1b[B":  # Down arrow
                current_idx = (current_idx + 1) % len(items)
            elif ch == " ":  # Space - toggle selection
                current_item = items[current_idx]
                if current_item in selected:
                    selected.remove(current_item)
                else:
                    selected.add(current_item)
            elif ch == "\r" or ch == "\n":  # Enter - confirm
                break
            elif ch == "\x03":  # Ctrl+C - cancel
                print(CLEAR_SCREEN, end="")
                print("\nOperation cancelled.")
                sys.exit(0)

        # Clear screen on exit
        print(CLEAR_SCREEN, end="")

    except ImportError:
        # Fallback for systems without tty/termios (e.g., Windows)
        print(f"{BOLD}Select MCPs to enable for this project:{RESET}")
        print()
        print("Available MCPs:")
        for idx, item in enumerate(items):
            status = " [preselected]" if item in selected else ""
            print(f"  {idx + 1}. {item}{status}")

        print()
        print("Enter comma-separated numbers (e.g., 1,3,5) or press Enter for defaults:")
        user_input = sys.stdin.readline().strip()

        if user_input:
            # Parse user selection
            selected = set()
            try:
                for num_str in user_input.split(","):
                    idx = int(num_str.strip()) - 1
                    if 0 <= idx < len(items):
                        selected.add(items[idx])
            except ValueError:
                print("Invalid input. Using defaults.")
                selected = set(preselected) & set(items)

    return list(selected)


def load_project_config(project_dir: Path) -> set[str] | None:
    """Load existing project config if present.

    ABOUTME: Returns set of server names or None if no config exists
    ABOUTME: Reads .mcpx.json file

    Args:
        project_dir: Path to project directory

    Returns:
        Set of server names if config exists, None otherwise
    """
    config_file = project_dir / ".mcpx.json"

    if not config_file.exists():
        return None

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        mcpx_section = data.get("mcpx", {})
        servers_list = mcpx_section.get("servers", [])

        return set(servers_list)

    except Exception:
        return None


def save_project_config(project_dir: Path, servers: list[str]) -> None:
    """Save project-level MCP configuration.

    ABOUTME: Writes .mcpx.json file
    ABOUTME: Uses simple JSON structure

    Args:
        project_dir: Path to project directory
        servers: List of server names to enable
    """
    config_file = project_dir / ".mcpx.json"

    # Simple JSON writing
    config_data = {
        "mcpx": {
            "version": "1.0",
            "servers": servers
        }
    }

    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)
        f.write("\n")


def sync_to_project_platforms(servers: dict[str, MCPServer], project_dir: Path) -> None:
    """Sync selected servers to platforms with project-level support.

    ABOUTME: Only syncs to Claude Code, Roo Code, Kilo Code
    ABOUTME: Creates project-level config files

    Args:
        servers: Dict of servers to sync
        project_dir: Path to project directory
    """
    from mcpx.platforms.claude import ClaudeAdapter
    from mcpx.platforms.kilo import KiloAdapter
    from mcpx.platforms.roo import RooAdapter

    # Platforms with project-level support
    platforms_with_project = [
        ClaudeAdapter(),
        RooAdapter(),
        KiloAdapter(),
    ]

    print()
    print("Syncing to project-level configs...")

    for platform in platforms_with_project:
        try:
            platform.save_project(servers, project_dir)
            print(f"  {GREEN}✓{RESET} {platform.name} - {len(servers)} servers")
        except Exception as e:
            print(f"  {YELLOW}⊘{RESET} {platform.name} - no project-level support ({e})")


def cmd_init() -> int:
    """Interactive project-level MCP selection.

    ABOUTME: Loads global config and presents interactive selection
    ABOUTME: Writes .mcpx.toml and syncs to project-level platforms
    ABOUTME: Returns exit code (0 for success, 1 for error)
    """
    from mcpx import __version__

    # Print header
    print(f"mcpx init v{__version__}")
    print()

    try:
        # Load global config
        global_config_path = get_config_path()
        print(f"Loading global MCPs from {global_config_path}...")

        global_config = load_config(global_config_path)

        server_count = len(global_config.servers)
        print(f"Found {server_count} server(s) available.")
        print()

        # Get current directory
        project_dir = Path.cwd()

        # Load existing project config if present
        existing_selection = load_project_config(project_dir)

        # Prepare server names for selection
        server_names = list(global_config.servers.keys())

        # Interactive selection
        selected_names = interactive_select(
            server_names,
            preselected=existing_selection if existing_selection else set(server_names)
        )

        if not selected_names:
            print()
            print("No servers selected. Project initialization cancelled.")
            return 0

        print()
        print(f"Creating .mcpx.json with {len(selected_names)} server(s)...")

        # Save project config
        save_project_config(project_dir, selected_names)

        # Get selected servers
        selected_servers = {
            name: global_config.servers[name]
            for name in selected_names
            if name in global_config.servers
        }

        # Sync to project-level platforms
        sync_to_project_platforms(selected_servers, project_dir)

        print()
        print("Project initialized! Run 'mcpx init' again to modify selection.")

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print()
        print("Global config not found. Run 'mcpx sync' first to create it.")
        return 1
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1
