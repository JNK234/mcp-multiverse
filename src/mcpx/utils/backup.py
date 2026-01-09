# Backup utilities for platform configuration files
import shutil
from datetime import datetime
from pathlib import Path
from typing import Literal

# ABOUTME: Supported platforms for backup naming
PlatformName = Literal[
    "claude",
    "gemini",
    "codex",
    "roo",
    "kilo",
    "cline",
]


def create_backup(source_path: Path, backup_dir: Path) -> Path:
    """Create a timestamped backup of a file.

    ABOUTME: Backup format: {platform}_{YYYYMMDD}_{HHMMSS}.{ext}
    ABOUTME: Uses shutil.copy2() to preserve file metadata
    ABOUTME: Creates backup_dir if it doesn't exist

    Args:
        source_path: Path to file to backup
        backup_dir: Directory where backup should be created

    Returns:
        Path to created backup file

    Raises:
        FileNotFoundError: If source_path doesn't exist
        OSError: If backup creation fails

    Examples:
        >>> source = Path("~/.claude.json").expanduser()
        >>> backup_dir = Path("~/.mcpx/backups").expanduser()
        >>> backup_path = create_backup(source, backup_dir)
        >>> backup_path.name
        'claude_20260108_143022.json'
    """
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    # Ensure backup directory exists
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Extract platform name from parent dir or use filename stem
    # e.g., ~/.claude.json -> claude
    # e.g., settings.json -> settings
    filename = source_path.name
    platform = filename.replace(".", "_").split("_")[0]

    # Build backup filename: {platform}_{YYYYMMDD}_{HHMMSS}.{ext}
    extension = source_path.suffix
    backup_filename = f"{platform}_{timestamp}{extension}"
    backup_path = backup_dir / backup_filename

    # Copy file with metadata preservation
    shutil.copy2(source_path, backup_path)

    return backup_path


def get_backup_dir() -> Path:
    """Get the default backup directory path.

    ABOUTME: Returns ~/.mcpx/backups
    ABOUTME: Does not create the directory

    Returns:
        Path to backup directory

    Examples:
        >>> get_backup_dir()
        PosixPath('/Users/user/.mcpx/backups')
    """
    return Path.home() / ".mcpx" / "backups"
