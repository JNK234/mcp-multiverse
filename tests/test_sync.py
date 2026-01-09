# Tests for sync orchestration
from pathlib import Path

from mcpx.models import MCPServer
from mcpx.sync import SyncReport, merge_servers, sync_all


class TestSyncReport:
    """Tests for SyncReport dataclass."""

    def test_initialization(self):
        """Test report initialization."""
        report = SyncReport(platforms_synced=0, platforms_total=2)

        assert report.platforms_synced == 0
        assert report.platforms_total == 2
        assert report.servers_synced == {}
        assert report.errors == []

    def test_add_platform_result_success(self):
        """Test adding successful platform result."""
        report = SyncReport(platforms_synced=0, platforms_total=2)

        report.add_platform_result("Claude Code", 5)

        assert report.platforms_synced == 1
        assert report.servers_synced == {"Claude Code": 5}

    def test_add_platform_result_zero(self):
        """Test adding platform result with zero servers."""
        report = SyncReport(platforms_synced=0, platforms_total=2)

        report.add_platform_result("Gemini CLI", 0)

        # Should not increment synced count if zero
        assert report.platforms_synced == 0
        assert report.servers_synced == {"Gemini CLI": 0}

    def test_add_error(self):
        """Test adding error to report."""
        report = SyncReport(platforms_synced=0, platforms_total=2)

        report.add_error("Platform not found")

        assert report.errors == ["Platform not found"]

    def test_multiple_errors(self):
        """Test adding multiple errors."""
        report = SyncReport(platforms_synced=0, platforms_total=2)

        report.add_error("Error 1")
        report.add_error("Error 2")

        assert len(report.errors) == 2
        assert report.errors == ["Error 1", "Error 2"]


class TestMergeServers:
    """Tests for merge_servers function."""

    def test_merge_empty_existing(self):
        """Test merging when existing is empty."""
        managed = {
            "server1": MCPServer(name="server1", command="npx", args=["-y", "pkg1"])
        }
        existing = {}

        result = merge_servers(managed, existing)

        assert result == managed
        assert len(result) == 1

    def test_merge_empty_managed(self):
        """Test merging when managed is empty (all orphans)."""
        managed = {}
        existing = {
            "orphan1": MCPServer(name="orphan1", command="npx", args=["-y", "pkg1"])
        }

        result = merge_servers(managed, existing)

        assert result == existing
        assert "orphan1" in result

    def test_merge_no_overlap(self):
        """Test merging with no overlapping servers."""
        managed = {
            "server1": MCPServer(name="server1", command="npx", args=["-y", "pkg1"])
        }
        existing = {
            "orphan1": MCPServer(name="orphan1", command="npx", args=["-y", "pkg2"])
        }

        result = merge_servers(managed, existing)

        assert len(result) == 2
        assert "server1" in result
        assert "orphan1" in result

    def test_merge_with_overlap(self):
        """Test merging where managed overrides existing."""
        managed = {
            "server1": MCPServer(name="server1", command="npx", args=["-y", "new_pkg"])
        }
        existing = {
            "server1": MCPServer(name="server1", command="npx", args=["-y", "old_pkg"]),
            "orphan1": MCPServer(name="orphan1", command="npx", args=["-y", "pkg2"])
        }

        result = merge_servers(managed, existing)

        assert len(result) == 2
        # Managed version should override
        assert result["server1"].args == ["-y", "new_pkg"]
        # Orphan should be preserved
        assert "orphan1" in result

    def test_merge_does_not_mutate_inputs(self):
        """Test that merge doesn't modify input dicts."""
        managed = {
            "server1": MCPServer(name="server1", command="npx", args=["-y", "pkg1"])
        }
        existing = {
            "orphan1": MCPServer(name="orphan1", command="npx", args=["-y", "pkg2"])
        }

        # Store original values
        managed_args_before = managed["server1"].args.copy()

        merge_servers(managed, existing)

        # Verify inputs weren't mutated
        assert managed["server1"].args == managed_args_before
        assert "server1" not in existing


class TestSyncAll:
    """Tests for sync_all function."""

    def test_sync_all_with_valid_config(self, tmp_path, monkeypatch):
        """Test sync with valid config and mock platforms."""
        # Create temporary config
        config_content = """
[mcpx]
version = "1.0"

[servers.test1]
command = "npx"
args = ["-y", "@test/server1"]

[servers.test2]
command = "npx"
args = ["-y", "@test/server2"]
"""
        config_file = tmp_path / "config.toml"
        config_file.write_text(config_content)

        # Mock platform adapters

        class MockPlatform:
            def __init__(self, name: str, config_path: Path):
                self._name = name
                self._config_path = config_path

            @property
            def name(self) -> str:
                return self._name

            @property
            def config_path(self) -> Path | None:
                return self._config_path

            def load(self) -> dict:
                return {}

            def save(self, servers: dict) -> None:
                # Create a simple marker file to indicate sync happened
                marker = self._config_path.parent / f"{self._name}_synced.txt"
                marker.write_text("synced")

        # Create mock platform configs
        claude_config = tmp_path / ".claude.json"
        claude_config.write_text('{"mcpServers": {}}')

        gemini_config = tmp_path / "settings.json"
        gemini_config.write_text('{"mcpServers": {}}')

        # Monkey patch get_all_platforms
        def mock_get_platforms():
            return [
                MockPlatform("Claude Code", claude_config),
                MockPlatform("Gemini CLI", gemini_config),
            ]

        monkeypatch.setattr("mcpx.sync.get_all_platforms", mock_get_platforms)

        # Mock backup and config loading
        from mcpx.config import load_config

        # Load config and sync
        config = load_config(config_file)
        report = sync_all(config)

        # Verify results
        assert report.platforms_total == 2
        assert report.platforms_synced == 2
        assert report.servers_synced["Claude Code"] == 2
        assert report.servers_synced["Gemini CLI"] == 2
        assert len(report.errors) == 0

    def test_sync_all_with_command_error(self, tmp_path, monkeypatch):
        """Test sync with server that has missing command."""
        # Create config with invalid command
        config_content = """
[mcpx]
version = "1.0"

[servers.invalid]
command = "nonexistent_command_xyz123"
args = []
"""
        config_file = tmp_path / "config.toml"
        config_file.write_text(config_content)

        # Mock platforms
        class MockPlatform:
            def __init__(self, name: str, config_path: Path):
                self._name = name
                self._config_path = config_path

            @property
            def name(self) -> str:
                return self._name

            @property
            def config_path(self) -> Path | None:
                return self._config_path

            def load(self) -> dict:
                return {}

            def save(self, servers: dict) -> None:
                pass

        claude_config = tmp_path / ".claude.json"
        claude_config.write_text('{"mcpServers": {}}')

        # Monkey patch
        def mock_get_platforms():
            return [MockPlatform("Claude Code", claude_config)]

        monkeypatch.setattr("mcpx.sync.get_all_platforms", mock_get_platforms)

        # Load and sync
        from mcpx.config import load_config

        config = load_config(config_file)
        report = sync_all(config)

        # Should fail validation and not sync
        assert len(report.errors) > 0
        assert "Command not found" in report.errors[0]
        assert report.platforms_synced == 0

    def test_sync_all_preserves_orphans(self, tmp_path, monkeypatch):
        """Test that sync preserves orphan servers."""
        # Create config
        config_content = """
[mcpx]
version = "1.0"

[servers.managed]
command = "npx"
args = ["-y", "@test/managed"]
"""
        config_file = tmp_path / "config.toml"
        config_file.write_text(config_content)

        # Mock platform with existing orphan
        class MockPlatform:
            def __init__(self, config_path: Path, existing_servers: dict):
                self._config_path = config_path
                self._existing = existing_servers
                self._saved = None

            @property
            def name(self) -> str:
                return "TestPlatform"

            @property
            def config_path(self) -> Path | None:
                return self._config_path

            def load(self) -> dict:
                return self._existing

            def save(self, servers: dict) -> None:
                self._saved = servers

        claude_config = tmp_path / ".claude.json"
        claude_config.write_text('{"mcpServers": {}}')  # Create the file
        orphan = MCPServer(name="orphan", command="python", args=["-m", "orphan"])

        platform = MockPlatform(claude_config, {"orphan": orphan})

        def mock_get_platforms():
            return [platform]

        monkeypatch.setattr("mcpx.sync.get_all_platforms", mock_get_platforms)

        # Load and sync
        from mcpx.config import load_config

        config = load_config(config_file)
        sync_all(config)

        # Verify both managed and orphan were saved
        assert "managed" in platform._saved
        assert "orphan" in platform._saved
        assert len(platform._saved) == 2
