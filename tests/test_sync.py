# ABOUTME: Tests for sync orchestration
# ABOUTME: Includes both unit tests with mocks and integration tests with real adapters
import json
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
            "server1": MCPServer(name="server1", type="stdio", command="npx", args=["-y", "pkg1"])
        }
        existing = {}

        result = merge_servers(managed, existing)

        assert result == managed
        assert len(result) == 1

    def test_merge_empty_managed(self):
        """Test merging when managed is empty (all orphans)."""
        managed = {}
        existing = {
            "orphan1": MCPServer(name="orphan1", type="stdio", command="npx", args=["-y", "pkg1"])
        }

        result = merge_servers(managed, existing)

        assert result == existing
        assert "orphan1" in result

    def test_merge_no_overlap(self):
        """Test merging with no overlapping servers."""
        managed = {
            "server1": MCPServer(name="server1", type="stdio", command="npx", args=["-y", "pkg1"])
        }
        existing = {
            "orphan1": MCPServer(name="orphan1", type="stdio", command="npx", args=["-y", "pkg2"])
        }

        result = merge_servers(managed, existing)

        assert len(result) == 2
        assert "server1" in result
        assert "orphan1" in result

    def test_merge_with_overlap(self):
        """Test merging where managed overrides existing."""
        managed = {
            "server1": MCPServer(name="server1", type="stdio", command="npx", args=["-y", "new_pkg"])
        }
        existing = {
            "server1": MCPServer(name="server1", type="stdio", command="npx", args=["-y", "old_pkg"]),
            "orphan1": MCPServer(name="orphan1", type="stdio", command="npx", args=["-y", "pkg2"])
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
            "server1": MCPServer(name="server1", type="stdio", command="npx", args=["-y", "pkg1"])
        }
        existing = {
            "orphan1": MCPServer(name="orphan1", type="stdio", command="npx", args=["-y", "pkg2"])
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
        # Create temporary config (JSON format)
        config_content = """{
  "mcpx": {
    "version": "1.0"
  },
  "servers": {
    "test1": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@test/server1"]
    },
    "test2": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@test/server2"]
    }
  }
}"""
        config_file = tmp_path / "config.json"
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
        # Create config with invalid command (JSON format)
        config_content = """{
  "mcpx": {
    "version": "1.0"
  },
  "servers": {
    "invalid": {
      "type": "stdio",
      "command": "nonexistent_command_xyz123",
      "args": []
    }
  }
}"""
        config_file = tmp_path / "config.json"
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
        # Create config (JSON format)
        config_content = """{
  "mcpx": {
    "version": "1.0"
  },
  "servers": {
    "managed": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@test/managed"]
    }
  }
}"""
        config_file = tmp_path / "config.json"
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
        orphan = MCPServer(name="orphan", type="stdio", command="python", args=["-m", "orphan"])

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


# =============================================================================
# Integration Tests - Real platform adapters
# =============================================================================


class TestIntegrationSyncWithRealAdapters:
    """Integration tests that use real platform adapters instead of mocks."""

    def test_integration_full_sync_flow_with_claude_adapter(self, tmp_path: Path):
        """Test the full sync flow: config file -> load -> sync to Claude adapter -> verify output.

        This test uses the real ClaudeAdapter with a temporary config file path.
        """
        from mcpx.config import load_config, save_config
        from mcpx.models import Config
        from mcpx.platforms.claude import ClaudeAdapter
        from mcpx.sync import merge_servers

        # Step 1: Create mcpx config file with servers
        config_file = tmp_path / "config.json"
        config = Config(
            version="1.0",
            servers={
                "filesystem": MCPServer(
                    name="filesystem",
                    type="stdio",
                    command="echo",  # Using echo as it exists on all systems
                    args=["filesystem-server"]
                ),
                "github": MCPServer(
                    name="github",
                    type="stdio",
                    command="echo",
                    args=["github-server"],
                    env={"GITHUB_TOKEN": "test-token"}
                )
            }
        )
        save_config(config_file, config)

        # Step 2: Verify config was saved correctly
        assert config_file.exists()
        loaded_config = load_config(config_file)
        assert len(loaded_config.servers) == 2
        assert "filesystem" in loaded_config.servers
        assert "github" in loaded_config.servers

        # Step 3: Create Claude adapter with temp path
        claude_config_path = tmp_path / ".claude.json"
        adapter = ClaudeAdapter(config_path=claude_config_path)

        # Step 4: Verify adapter properties
        assert adapter.name == "Claude Code"
        assert adapter.config_path is None  # File doesn't exist yet

        # Step 5: Load existing servers (should be empty)
        existing = adapter.load()
        assert existing == {}

        # Step 6: Merge and save servers
        merged = merge_servers(loaded_config.servers, existing)
        adapter.save(merged)

        # Step 7: Verify output file exists and contains correct data
        assert claude_config_path.exists()
        output_data = json.loads(claude_config_path.read_text())

        assert "mcpServers" in output_data
        assert "filesystem" in output_data["mcpServers"]
        assert "github" in output_data["mcpServers"]

        # Verify filesystem server details
        fs_server = output_data["mcpServers"]["filesystem"]
        assert fs_server["command"] == "echo"
        assert fs_server["args"] == ["filesystem-server"]

        # Verify github server details with env
        gh_server = output_data["mcpServers"]["github"]
        assert gh_server["command"] == "echo"
        assert gh_server["args"] == ["github-server"]
        assert gh_server["env"] == {"GITHUB_TOKEN": "test-token"}

        # Step 8: Reload and verify roundtrip
        reloaded = adapter.load()
        assert len(reloaded) == 2
        assert reloaded["filesystem"].command == "echo"
        assert reloaded["github"].env == {"GITHUB_TOKEN": "test-token"}

    def test_integration_sync_preserves_existing_servers(self, tmp_path: Path):
        """Test that syncing preserves servers that exist in the platform config but not in mcpx."""
        from mcpx.config import load_config, save_config
        from mcpx.models import Config
        from mcpx.platforms.claude import ClaudeAdapter
        from mcpx.sync import merge_servers

        # Step 1: Create initial Claude config with an "orphan" server
        claude_config_path = tmp_path / ".claude.json"
        initial_claude_config = {
            "mcpServers": {
                "orphan-server": {
                    "command": "node",
                    "args": ["orphan.js"]
                }
            }
        }
        claude_config_path.write_text(json.dumps(initial_claude_config, indent=2))

        # Step 2: Create mcpx config with a different server
        config_file = tmp_path / "config.json"
        config = Config(
            version="1.0",
            servers={
                "managed-server": MCPServer(
                    name="managed-server",
                    type="stdio",
                    command="echo",
                    args=["managed"]
                )
            }
        )
        save_config(config_file, config)

        # Step 3: Load, merge, and save
        loaded_config = load_config(config_file)
        adapter = ClaudeAdapter(config_path=claude_config_path)
        existing = adapter.load()

        # Verify orphan exists before merge
        assert "orphan-server" in existing

        merged = merge_servers(loaded_config.servers, existing)
        adapter.save(merged)

        # Step 4: Verify both servers exist after sync
        final_data = json.loads(claude_config_path.read_text())
        assert "mcpServers" in final_data
        assert "orphan-server" in final_data["mcpServers"]
        assert "managed-server" in final_data["mcpServers"]

    def test_integration_sync_http_server(self, tmp_path: Path):
        """Test syncing an HTTP type server."""
        from mcpx.config import save_config, load_config
        from mcpx.models import Config
        from mcpx.platforms.claude import ClaudeAdapter
        from mcpx.sync import merge_servers

        # Create config with HTTP server
        config_file = tmp_path / "config.json"
        config = Config(
            version="1.0",
            servers={
                "api-server": MCPServer(
                    name="api-server",
                    type="http",
                    url="https://api.example.com/mcp",
                    headers={"Authorization": "Bearer ${API_TOKEN}"}
                )
            }
        )
        save_config(config_file, config)

        # Load and sync
        loaded_config = load_config(config_file)
        claude_config_path = tmp_path / ".claude.json"
        adapter = ClaudeAdapter(config_path=claude_config_path)

        merged = merge_servers(loaded_config.servers, adapter.load())
        adapter.save(merged)

        # Verify HTTP server was saved correctly
        output_data = json.loads(claude_config_path.read_text())
        assert "api-server" in output_data["mcpServers"]
        api_server = output_data["mcpServers"]["api-server"]
        assert api_server["url"] == "https://api.example.com/mcp"
        assert api_server["headers"] == {"Authorization": "Bearer ${API_TOKEN}"}
