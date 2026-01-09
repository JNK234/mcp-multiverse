# Tests for backup utilities
from pathlib import Path

import pytest

from mcpx.utils.backup import create_backup, get_backup_dir


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
