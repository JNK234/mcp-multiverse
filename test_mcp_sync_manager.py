#!/usr/bin/env python3
"""
ABOUTME: Unit tests for MCP sync manager
ABOUTME: Tests MCP sync functionality across different platforms
"""

import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os

# Import the sync manager - use direct import for testing
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_sync_manager import MCPSyncManager, MCPServer, Platforms


class TestMCPServer(unittest.TestCase):
    """Test MCPServer dataclass functionality"""

    def test_to_dict(self):
        """Test conversion to dictionary"""
        server = MCPServer(
            command="npx",
            args=["-y", "server-name"],
            env={"KEY": "value"},
            disabled=False
        )

        result = server.to_dict()

        expected = {
            "command": "npx",
            "args": ["-y", "server-name"],
            "env": {"KEY": "value"},
            "disabled": False
        }
        self.assertEqual(result, expected)

    def test_from_dict(self):
        """Test creation from dictionary"""
        data = {
            "command": "python",
            "args": ["server.py"],
            "env": {"API_KEY": "secret"},
            "disabled": True,
            "autoApprove": ["tool1", "tool2"],
            "timeout": 120
        }

        server = MCPServer.from_dict(data)

        self.assertEqual(server.command, "python")
        self.assertEqual(server.args, ["server.py"])
        self.assertEqual(server.env, {"API_KEY": "secret"})
        self.assertEqual(server.disabled, True)
        self.assertEqual(server.auto_approve, ["tool1", "tool2"])
        self.assertEqual(server.timeout, 120)

    def test_minimal_server(self):
        """Test server with minimal configuration"""
        server = MCPServer(command="npx")
        result = server.to_dict()

        self.assertEqual(result, {"command": "npx"})


class TestPlatforms(unittest.TestCase):
    """Test platform configuration detection"""

    @patch('pathlib.Path.home')
    def test_platform_paths(self, mock_home):
        """Test that platform paths are correctly set"""
        mock_home.return_value = Path("/test/home")

        platforms = Platforms()

        # Test Claude paths
        self.assertEqual(
            str(platforms.claude_user_config),
            "/test/home/.claude/claude_desktop_config.json"
        )

        # Test Gemini paths
        self.assertEqual(
            str(platforms.gemini_config),
            "/test/home/.gemini/settings.json"
        )

        # Test Cline paths (macOS)
        self.assertEqual(
            str(platforms.cline_config),
            "/test/home/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json"
        )


class TestMCPSyncManager(unittest.TestCase):
    """Test main sync manager functionality"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = MCPSyncManager()
        self.manager.backup_dir = Path(self.temp_dir) / "backups"

    def create_test_config(self, platform_name: str, servers: dict) -> Path:
        """Create a test configuration file"""
        config_file = Path(self.temp_dir) / f"{platform_name}_config.json"
        config_data = {"mcpServers": servers}

        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)

        return config_file

    def test_extract_mcp_servers(self):
        """Test extraction of MCP servers from configuration"""
        servers_data = {
            "server1": {
                "command": "npx",
                "args": ["server1"],
                "env": {"KEY1": "value1"}
            },
            "server2": {
                "command": "python",
                "args": ["server2.py"]
            }
        }

        config = {"mcpServers": servers_data}
        extracted = self.manager.extract_mcp_servers(config)

        self.assertEqual(len(extracted), 2)
        self.assertIn("server1", extracted)
        self.assertIn("server2", extracted)
        self.assertEqual(extracted["server1"].command, "npx")
        self.assertEqual(extracted["server2"].command, "python")

    def test_merge_servers(self):
        """Test merging of server configurations"""
        existing = {
            "server1": MCPServer(command="old_command"),
            "server2": MCPServer(command="keep_command")
        }

        new = {
            "server1": MCPServer(command="new_command"),
            "server3": MCPServer(command="add_command")
        }

        merged = self.manager.merge_servers(existing, new)

        self.assertEqual(len(merged), 3)
        self.assertEqual(merged["server1"].command, "new_command")  # Updated
        self.assertEqual(merged["server2"].command, "keep_command")  # Kept
        self.assertEqual(merged["server3"].command, "add_command")  # Added

    def test_format_for_platform_claude(self):
        """Test formatting for Claude platform"""
        servers = {
            "test": MCPServer(command="npx", args=["test"])
        }

        formatted = self.manager.format_for_platform(servers, "claude")

        self.assertIn("mcpServers", formatted)
        self.assertEqual(len(formatted), 1)  # Only mcpServers
        self.assertIn("test", formatted["mcpServers"])
        self.assertEqual(formatted["mcpServers"]["test"]["command"], "npx")

    def test_format_for_platform_gemini(self):
        """Test formatting for Gemini platform"""
        servers = {
            "test": MCPServer(command="npx", args=["test"])
        }

        formatted = self.manager.format_for_platform(servers, "gemini")

        self.assertIn("mcpServers", formatted)
        self.assertIn("general", formatted)
        self.assertIn("security", formatted)
        self.assertIn("ui", formatted)
        self.assertIn("output", formatted)

    def test_format_for_platform_cline(self):
        """Test formatting for Cline platform"""
        servers = {
            "test": MCPServer(command="npx", args=["test"])
        }

        formatted = self.manager.format_for_platform(servers, "cline")

        server_data = formatted["mcpServers"]["test"]
        self.assertIn("disabled", server_data)
        self.assertIn("autoApprove", server_data)
        self.assertIn("timeout", server_data)
        self.assertIn("transportType", server_data)
        self.assertEqual(server_data["timeout"], 60)
        self.assertEqual(server_data["transportType"], "stdio")

    def test_backup_config(self):
        """Test backup functionality"""
        test_file = Path(self.temp_dir) / "test_config.json"
        test_data = {"test": "data"}

        with open(test_file, 'w') as f:
            json.dump(test_data, f)

        backup_path = self.manager.backup_config(test_file, "test_platform")

        self.assertIsNotNone(backup_path)
        self.assertTrue(backup_path.exists())
        self.assertIn("test_platform", backup_path.name)
        self.assertIn("test_config.json", backup_path.name)

        # Verify backup content
        with open(backup_path, 'r') as f:
            backup_data = json.load(f)

        self.assertEqual(backup_data, test_data)

    def test_load_json_valid(self):
        """Test loading valid JSON"""
        test_file = Path(self.temp_dir) / "valid.json"
        test_data = {"key": "value"}

        with open(test_file, 'w') as f:
            json.dump(test_data, f)

        loaded = self.manager.load_json(test_file)
        self.assertEqual(loaded, test_data)

    def test_load_json_invalid(self):
        """Test loading invalid JSON"""
        test_file = Path(self.temp_dir) / "invalid.json"

        with open(test_file, 'w') as f:
            f.write("invalid json content")

        loaded = self.manager.load_json(test_file)
        self.assertIsNone(loaded)

    def test_save_json(self):
        """Test saving JSON file"""
        test_file = Path(self.temp_dir) / "save_test.json"
        test_data = {"key": "value"}

        success = self.manager.save_json(test_file, test_data)

        self.assertTrue(success)
        self.assertTrue(test_file.exists())

        with open(test_file, 'r') as f:
            saved_data = json.load(f)

        self.assertEqual(saved_data, test_data)

    def test_convert_between_formats(self):
        """Test that servers can be converted between formats without data loss"""
        original = MCPServer(
            command="npx",
            args=["-y", "server"],
            env={"KEY": "value"},
            disabled=False,
            timeout=120
        )

        # Convert to dict and back
        as_dict = original.to_dict()
        recreated = MCPServer.from_dict(as_dict)

        self.assertEqual(recreated.command, original.command)
        self.assertEqual(recreated.args, original.args)
        self.assertEqual(recreated.env, original.env)
        self.assertEqual(recreated.disabled, original.disabled)
        self.assertEqual(recreated.timeout, original.timeout)


class TestIntegration(unittest.TestCase):
    """Integration tests for full sync workflow"""

    def setUp(self):
        """Set up test environment with mock platform configs"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = MCPSyncManager()
        self.manager.backup_dir = Path(self.temp_dir) / "backups"

    def test_full_sync_workflow(self):
        """Test a complete sync workflow"""
        # Create test server data
        test_servers = {
            "github": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {
                    "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_test_token"
                }
            }
        }

        # Create config files for different platforms
        claude_config = {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home"]
                }
            }
        }

        gemini_config = {
            "mcpServers": test_servers,
            "general": {},
            "security": {}
        }

        # Mock the platform config paths
        with patch.object(self.manager.platforms, 'claude_user_config', Path(self.temp_dir) / 'claude.json'), \
             patch.object(self.manager.platforms, 'gemini_config', Path(self.temp_dir) / 'gemini.json'), \
             patch.object(self.manager.platforms, 'cline_config', Path(self.temp_dir) / 'cline.json'), \
             patch.object(self.manager.platforms, 'roo_config', Path(self.temp_dir) / 'roo.json'):

            # Create initial configs
            self.manager.save_json(self.manager.platforms.claude_user_config, claude_config)
            self.manager.save_json(self.manager.platforms.gemini_config, gemini_config)

            # Perform sync
            results = self.manager.sync_all()

            # Verify all platforms were processed
            self.assertEqual(len(results), 4)

            # Verify files were created
            self.assertTrue(self.manager.platforms.claude_user_config.exists())
            self.assertTrue(self.manager.platforms.gemini_config.exists())
            self.assertTrue(self.manager.platforms.cline_config.exists())
            self.assertTrue(self.manager.platforms.roo_config.exists())

            # Verify content
            claude_result = self.manager.load_json(self.manager.platforms.claude_user_config)
            self.assertIn("mcpServers", claude_result)
            self.assertIn("github", claude_result["mcpServers"])
            self.assertIn("filesystem", claude_result["mcpServers"])


if __name__ == "__main__":
    unittest.main()
