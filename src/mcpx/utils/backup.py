# ABOUTME: Backup utilities for platform configuration files.
# ABOUTME: Handles timestamped backups with automatic retention cleanup (keep last 5 per platform).
import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

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

    # Clean up old backups (keep last 5 per platform)
    cleanup_old_backups(backup_dir)

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


def cleanup_old_backups(backup_dir: Path, max_backups_per_platform: int = 5) -> list[Path]:
    """Remove old backup files, keeping only the most recent per platform.

    ABOUTME: Groups backups by platform prefix (before _timestamp)
    ABOUTME: Sorts by timestamp descending (newest first)
    ABOUTME: Deletes backups beyond max_backups_per_platform for each platform
    ABOUTME: Logs warnings on errors but does not raise exceptions

    Args:
        backup_dir: Directory containing backup files
        max_backups_per_platform: Maximum backups to keep per platform (default 5)

    Returns:
        List of paths that were deleted

    Examples:
        >>> backup_dir = Path("~/.mcpx/backups").expanduser()
        >>> deleted = cleanup_old_backups(backup_dir)
        >>> len(deleted)
        3
    """
    deleted_files: list[Path] = []

    if not backup_dir.exists():
        return deleted_files

    # Pattern matches: {platform}_{YYYYMMDD}_{HHMMSS}.{ext}
    # e.g., claude_20260108_143022.json
    backup_pattern = re.compile(r"^(.+?)_(\d{8}_\d{6})\.(.+)$")

    # Group backup files by platform
    backups_by_platform: dict[str, list[tuple[str, Path]]] = {}

    for file_path in backup_dir.iterdir():
        if not file_path.is_file():
            continue

        match = backup_pattern.match(file_path.name)
        if not match:
            continue

        platform = match.group(1)
        timestamp = match.group(2)

        if platform not in backups_by_platform:
            backups_by_platform[platform] = []
        backups_by_platform[platform].append((timestamp, file_path))

    # For each platform, sort by timestamp (newest first) and delete old ones
    for platform, backups in backups_by_platform.items():
        # Sort by timestamp descending (newest first)
        backups.sort(key=lambda x: x[0], reverse=True)

        # Keep only the first max_backups_per_platform, delete the rest
        backups_to_delete = backups[max_backups_per_platform:]

        for timestamp, file_path in backups_to_delete:
            try:
                file_path.unlink()
                deleted_files.append(file_path)
                logger.debug(f"Deleted old backup: {file_path}")
            except OSError as e:
                logger.warning(f"Failed to delete old backup {file_path}: {e}")

    return deleted_files
