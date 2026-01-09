# ABOUTME: Tests for backup utilities.
# ABOUTME: Covers create_backup, get_backup_dir, and cleanup_old_backups functions.
from pathlib import Path

import pytest

from mcpx.utils.backup import cleanup_old_backups, create_backup, get_backup_dir


class TestGetBackupDir:
    """Tests for get_backup_dir function."""

    def test_returns_path_object(self):
        """Test that get_backup_dir returns a Path object."""
        backup_dir = get_backup_dir()
        assert isinstance(backup_dir, Path)

    def test_backup_dir_location(self):
        """Test that backup dir is in home directory."""
        backup_dir = get_backup_dir()
        # Should be ~/.mcpx/backups
        assert backup_dir.parent.name == ".mcpx"
        assert backup_dir.name == "backups"

    def test_backup_dir_is_absolute(self):
        """Test that backup dir path is absolute."""
        backup_dir = get_backup_dir()
        assert backup_dir.is_absolute()


class TestCreateBackup:
    """Tests for create_backup function."""

    def test_creates_backup_file(self, tmp_path):
        """Test that backup file is created."""
        # Create source file
        source = tmp_path / "test.json"
        source.write_text('{"test": "data"}')

        backup_dir = tmp_path / "backups"
        backup_path = create_backup(source, backup_dir)

        assert backup_path.exists()
        assert backup_dir.exists()

    def test_backup_preserves_content(self, tmp_path):
        """Test that backup preserves file content."""
        source = tmp_path / "config.json"
        original_content = '{"servers": {"test": {"command": "node"}}}'
        source.write_text(original_content)

        backup_dir = tmp_path / "backups"
        backup_path = create_backup(source, backup_dir)

        backup_content = backup_path.read_text()
        assert backup_content == original_content

    def test_backup_filename_format(self, tmp_path):
        """Test that backup filename follows format: {platform}_{YYYYMMDD}_{HHMMSS}.{ext}"""
        source = tmp_path / "claude.json"
        source.write_text("{}")

        backup_dir = tmp_path / "backups"
        backup_path = create_backup(source, backup_dir)

        # Filename should match pattern: claude_YYYYMMDD_HHMMSS.json
        import re
        pattern = r'^claude_\d{8}_\d{6}\.json$'
        assert re.match(pattern, backup_path.name)

    def test_creates_backup_dir_if_missing(self, tmp_path):
        """Test that backup directory is created if it doesn't exist."""
        source = tmp_path / "test.json"
        source.write_text("{}")

        backup_dir = tmp_path / "new_backups" / "nested"
        assert not backup_dir.exists()

        backup_path = create_backup(source, backup_dir)

        assert backup_dir.exists()
        assert backup_path.exists()

    def test_source_file_not_found(self, tmp_path):
        """Test that FileNotFoundError is raised for missing source."""
        source = tmp_path / "nonexistent.json"
        backup_dir = tmp_path / "backups"

        with pytest.raises(FileNotFoundError):
            create_backup(source, backup_dir)

    def test_metadata_preservation(self, tmp_path):
        """Test that shutil.copy2 preserves file metadata."""
        source = tmp_path / "test.json"
        source.write_text("{}")

        backup_dir = tmp_path / "backups"
        backup_path = create_backup(source, backup_dir)

        # Metadata should be preserved (using copy2)
        stat_source = source.stat()
        stat_backup = backup_path.stat()

        # File size should be same
        assert stat_source.st_size == stat_backup.st_size

    def test_json_extension(self, tmp_path):
        """Test backup with .json extension."""
        source = tmp_path / "gemini.json"
        source.write_text("{}")

        backup_dir = tmp_path / "backups"
        backup_path = create_backup(source, backup_dir)

        assert backup_path.suffix == ".json"

    def test_toml_extension(self, tmp_path):
        """Test backup with .toml extension."""
        source = tmp_path / "codex.toml"
        source.write_text("[test]")

        backup_dir = tmp_path / "backups"
        backup_path = create_backup(source, backup_dir)

        assert backup_path.suffix == ".toml"

    def test_platform_name_extraction(self, tmp_path):
        """Test that platform name is correctly extracted from filename."""
        # Test with claude.json -> claude
        source = tmp_path / "claude.json"
        source.write_text("{}")

        backup_dir = tmp_path / "backups"
        backup_path = create_backup(source, backup_dir)

        # Should start with platform name
        assert backup_path.name.startswith("claude_")

    def test_returns_backup_path(self, tmp_path):
        """Test that create_backup returns the backup file path."""
        source = tmp_path / "test.json"
        source.write_text("{}")

        backup_dir = tmp_path / "backups"
        backup_path = create_backup(source, backup_dir)

        assert isinstance(backup_path, Path)
        assert backup_path.is_absolute()


class TestCleanupOldBackups:
    """Tests for cleanup_old_backups function."""

    def test_returns_empty_list_for_nonexistent_dir(self, tmp_path):
        """Test that cleanup returns empty list if backup dir doesn't exist."""
        backup_dir = tmp_path / "nonexistent"
        deleted = cleanup_old_backups(backup_dir)
        assert deleted == []

    def test_returns_empty_list_for_empty_dir(self, tmp_path):
        """Test that cleanup returns empty list for empty directory."""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        deleted = cleanup_old_backups(backup_dir)
        assert deleted == []

    def test_keeps_last_5_backups_per_platform(self, tmp_path):
        """Test that only the last 5 backups per platform are kept."""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        # Create 7 backups for 'claude' platform
        for i in range(7):
            backup_file = backup_dir / f"claude_20260101_00000{i}.json"
            backup_file.write_text("{}")

        deleted = cleanup_old_backups(backup_dir)

        # Should have deleted 2 (oldest)
        assert len(deleted) == 2
        # Should have 5 remaining
        remaining = list(backup_dir.glob("claude_*.json"))
        assert len(remaining) == 5

    def test_keeps_newest_backups(self, tmp_path):
        """Test that the newest backups are kept, oldest deleted."""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        # Create 7 backups with different timestamps
        timestamps = [
            "20260101_100000",
            "20260101_110000",
            "20260101_120000",
            "20260101_130000",
            "20260101_140000",
            "20260101_150000",
            "20260101_160000",
        ]
        for ts in timestamps:
            backup_file = backup_dir / f"gemini_{ts}.json"
            backup_file.write_text("{}")

        deleted = cleanup_old_backups(backup_dir)

        # The oldest 2 should be deleted
        deleted_names = [p.name for p in deleted]
        assert "gemini_20260101_100000.json" in deleted_names
        assert "gemini_20260101_110000.json" in deleted_names

        # The newest 5 should remain
        remaining = list(backup_dir.glob("gemini_*.json"))
        remaining_names = [p.name for p in remaining]
        assert "gemini_20260101_120000.json" in remaining_names
        assert "gemini_20260101_160000.json" in remaining_names

    def test_handles_multiple_platforms_independently(self, tmp_path):
        """Test that each platform is handled independently."""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        # Create 7 backups for 'claude' and 3 for 'gemini'
        for i in range(7):
            (backup_dir / f"claude_20260101_00000{i}.json").write_text("{}")
        for i in range(3):
            (backup_dir / f"gemini_20260101_00000{i}.json").write_text("{}")

        deleted = cleanup_old_backups(backup_dir)

        # Should delete 2 from claude, 0 from gemini
        assert len(deleted) == 2
        deleted_names = [p.name for p in deleted]
        assert all("claude" in name for name in deleted_names)

        # Verify counts
        claude_remaining = list(backup_dir.glob("claude_*.json"))
        gemini_remaining = list(backup_dir.glob("gemini_*.json"))
        assert len(claude_remaining) == 5
        assert len(gemini_remaining) == 3

    def test_ignores_non_matching_files(self, tmp_path):
        """Test that files not matching backup pattern are ignored."""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        # Create files that don't match the pattern
        (backup_dir / "readme.txt").write_text("readme")
        (backup_dir / "random_file.json").write_text("{}")
        (backup_dir / "claude.json").write_text("{}")  # Missing timestamp

        # Create 3 valid backups
        for i in range(3):
            (backup_dir / f"claude_20260101_00000{i}.json").write_text("{}")

        deleted = cleanup_old_backups(backup_dir)

        # No files should be deleted (less than 5 valid backups)
        assert len(deleted) == 0
        # Non-matching files should still exist
        assert (backup_dir / "readme.txt").exists()
        assert (backup_dir / "random_file.json").exists()
        assert (backup_dir / "claude.json").exists()

    def test_respects_custom_max_backups(self, tmp_path):
        """Test that max_backups_per_platform parameter is respected."""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        # Create 5 backups
        for i in range(5):
            (backup_dir / f"claude_20260101_00000{i}.json").write_text("{}")

        # Keep only 2
        deleted = cleanup_old_backups(backup_dir, max_backups_per_platform=2)

        assert len(deleted) == 3
        remaining = list(backup_dir.glob("claude_*.json"))
        assert len(remaining) == 2

    def test_handles_different_extensions(self, tmp_path):
        """Test that files with different extensions are handled correctly."""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        # Create backups with different extensions
        for i in range(7):
            (backup_dir / f"codex_20260101_00000{i}.toml").write_text("")

        deleted = cleanup_old_backups(backup_dir)

        # Should delete oldest 2
        assert len(deleted) == 2
        remaining = list(backup_dir.glob("codex_*.toml"))
        assert len(remaining) == 5

    def test_ignores_directories(self, tmp_path):
        """Test that directories are ignored during cleanup."""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        # Create a directory that matches backup pattern
        subdir = backup_dir / "claude_20260101_000000.json"
        subdir.mkdir()

        deleted = cleanup_old_backups(backup_dir)

        # Directory should not be deleted
        assert len(deleted) == 0
        assert subdir.exists()

    def test_create_backup_triggers_cleanup(self, tmp_path):
        """Test that create_backup automatically cleans up old backups."""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        # Pre-create 5 old backups
        for i in range(5):
            (backup_dir / f"testfile_20260101_00000{i}.json").write_text("{}")

        # Create source file and run create_backup
        source = tmp_path / "testfile.json"
        source.write_text("{}")

        # This should create a 6th backup and delete the oldest
        create_backup(source, backup_dir)

        # Should have exactly 5 backups
        remaining = list(backup_dir.glob("testfile_*.json"))
        assert len(remaining) == 5
