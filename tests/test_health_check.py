# ABOUTME: Tests for health check functionality for stdio MCP servers
# ABOUTME: Covers success, failure, timeout, and edge cases
import json
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from mcpx.models import MCPServer
from mcpx.utils.validation import (
    HEALTH_CHECK_TIMEOUT,
    MCP_CLIENT_NAME,
    MCP_CLIENT_VERSION,
    MCP_PROTOCOL_VERSION,
    health_check_stdio_server,
)


class TestHealthCheckStdioServer:
    """Tests for health_check_stdio_server function."""

    def test_non_stdio_server_fails(self):
        """Test that HTTP server type returns failure."""
        server = MCPServer(
            name="http-server",
            type="http",
            url="https://example.com/mcp"
        )
        success, message = health_check_stdio_server(server)
        assert success is False
        assert "not a stdio server" in message
        assert "http-server" in message

    def test_missing_command_fails(self):
        """Test that server without command returns failure."""
        server = MCPServer(
            name="no-cmd-server",
            type="stdio",
            command=None
        )
        success, message = health_check_stdio_server(server)
        assert success is False
        assert "no command specified" in message
        assert "no-cmd-server" in message

    def test_nonexistent_command_fails(self):
        """Test that non-existent command returns failure."""
        server = MCPServer(
            name="bad-cmd-server",
            type="stdio",
            command="definitely_not_a_real_command_xyz123"
        )
        success, message = health_check_stdio_server(server)
        assert success is False
        assert "Command not found" in message
        assert "bad-cmd-server" in message

    @patch("mcpx.utils.validation.subprocess.Popen")
    @patch("mcpx.utils.validation.validate_command_exists")
    def test_successful_health_check(self, mock_validate, mock_popen):
        """Test successful health check with valid MCP response."""
        mock_validate.return_value = None

        # Create mock process
        mock_process = MagicMock()
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "serverInfo": {
                    "name": "test-mcp-server",
                    "version": "1.0.0"
                },
                "capabilities": {}
            }
        }
        mock_process.communicate.return_value = (
            json.dumps(mock_response).encode("utf-8"),
            b""
        )
        mock_popen.return_value = mock_process

        server = MCPServer(
            name="test-server",
            type="stdio",
            command="test-cmd",
            args=["-y", "test-package"]
        )
        success, message = health_check_stdio_server(server)

        assert success is True
        assert "healthy" in message
        assert "test-server" in message
        assert "test-mcp-server" in message
        assert "1.0.0" in message

        # Verify process was cleaned up
        mock_process.terminate.assert_called_once()

    @patch("mcpx.utils.validation.subprocess.Popen")
    @patch("mcpx.utils.validation.validate_command_exists")
    def test_timeout_returns_failure(self, mock_validate, mock_popen):
        """Test that timeout during communication returns failure."""
        mock_validate.return_value = None

        mock_process = MagicMock()
        mock_process.communicate.side_effect = subprocess.TimeoutExpired(
            cmd=["test-cmd"], timeout=5
        )
        mock_popen.return_value = mock_process

        server = MCPServer(
            name="slow-server",
            type="stdio",
            command="test-cmd"
        )
        success, message = health_check_stdio_server(server)

        assert success is False
        assert "timed out" in message
        assert "slow-server" in message
        assert str(HEALTH_CHECK_TIMEOUT) in message

    @patch("mcpx.utils.validation.subprocess.Popen")
    @patch("mcpx.utils.validation.validate_command_exists")
    def test_custom_timeout(self, mock_validate, mock_popen):
        """Test that custom timeout is used."""
        mock_validate.return_value = None

        mock_process = MagicMock()
        mock_process.communicate.side_effect = subprocess.TimeoutExpired(
            cmd=["test-cmd"], timeout=10
        )
        mock_popen.return_value = mock_process

        server = MCPServer(
            name="slow-server",
            type="stdio",
            command="test-cmd"
        )
        success, message = health_check_stdio_server(server, timeout=10)

        assert success is False
        assert "10" in message

    @patch("mcpx.utils.validation.subprocess.Popen")
    @patch("mcpx.utils.validation.validate_command_exists")
    def test_empty_response_fails(self, mock_validate, mock_popen):
        """Test that empty response returns failure."""
        mock_validate.return_value = None

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_popen.return_value = mock_process

        server = MCPServer(
            name="silent-server",
            type="stdio",
            command="test-cmd"
        )
        success, message = health_check_stdio_server(server)

        assert success is False
        assert "no response" in message
        assert "silent-server" in message

    @patch("mcpx.utils.validation.subprocess.Popen")
    @patch("mcpx.utils.validation.validate_command_exists")
    def test_stderr_included_in_failure(self, mock_validate, mock_popen):
        """Test that stderr is included in failure message when no stdout."""
        mock_validate.return_value = None

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"Error: initialization failed")
        mock_popen.return_value = mock_process

        server = MCPServer(
            name="error-server",
            type="stdio",
            command="test-cmd"
        )
        success, message = health_check_stdio_server(server)

        assert success is False
        assert "no response" in message
        assert "stderr" in message
        assert "initialization failed" in message

    @patch("mcpx.utils.validation.subprocess.Popen")
    @patch("mcpx.utils.validation.validate_command_exists")
    def test_non_json_response_fails(self, mock_validate, mock_popen):
        """Test that non-JSON response returns failure."""
        mock_validate.return_value = None

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"Not a JSON response", b"")
        mock_popen.return_value = mock_process

        server = MCPServer(
            name="bad-response-server",
            type="stdio",
            command="test-cmd"
        )
        success, message = health_check_stdio_server(server)

        assert success is False
        assert "non-JSON response" in message

    @patch("mcpx.utils.validation.subprocess.Popen")
    @patch("mcpx.utils.validation.validate_command_exists")
    def test_invalid_json_response_fails(self, mock_validate, mock_popen):
        """Test that invalid JSON response returns failure."""
        mock_validate.return_value = None

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"{invalid json}", b"")
        mock_popen.return_value = mock_process

        server = MCPServer(
            name="invalid-json-server",
            type="stdio",
            command="test-cmd"
        )
        success, message = health_check_stdio_server(server)

        assert success is False
        assert "invalid JSON" in message

    @patch("mcpx.utils.validation.subprocess.Popen")
    @patch("mcpx.utils.validation.validate_command_exists")
    def test_missing_jsonrpc_field_fails(self, mock_validate, mock_popen):
        """Test that response without jsonrpc field returns failure."""
        mock_validate.return_value = None

        mock_process = MagicMock()
        mock_response = {"id": 1, "result": {}}
        mock_process.communicate.return_value = (
            json.dumps(mock_response).encode("utf-8"),
            b""
        )
        mock_popen.return_value = mock_process

        server = MCPServer(
            name="no-jsonrpc-server",
            type="stdio",
            command="test-cmd"
        )
        success, message = health_check_stdio_server(server)

        assert success is False
        assert "missing 'jsonrpc' field" in message

    @patch("mcpx.utils.validation.subprocess.Popen")
    @patch("mcpx.utils.validation.validate_command_exists")
    def test_wrong_jsonrpc_version_fails(self, mock_validate, mock_popen):
        """Test that wrong JSON-RPC version returns failure."""
        mock_validate.return_value = None

        mock_process = MagicMock()
        mock_response = {"jsonrpc": "1.0", "id": 1, "result": {}}
        mock_process.communicate.return_value = (
            json.dumps(mock_response).encode("utf-8"),
            b""
        )
        mock_popen.return_value = mock_process

        server = MCPServer(
            name="old-jsonrpc-server",
            type="stdio",
            command="test-cmd"
        )
        success, message = health_check_stdio_server(server)

        assert success is False
        assert "invalid JSON-RPC version" in message

    @patch("mcpx.utils.validation.subprocess.Popen")
    @patch("mcpx.utils.validation.validate_command_exists")
    def test_error_response_returns_failure(self, mock_validate, mock_popen):
        """Test that MCP error response returns failure."""
        mock_validate.return_value = None

        mock_process = MagicMock()
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32600,
                "message": "Invalid request"
            }
        }
        mock_process.communicate.return_value = (
            json.dumps(mock_response).encode("utf-8"),
            b""
        )
        mock_popen.return_value = mock_process

        server = MCPServer(
            name="error-response-server",
            type="stdio",
            command="test-cmd"
        )
        success, message = health_check_stdio_server(server)

        assert success is False
        assert "returned error" in message
        assert "Invalid request" in message

    @patch("mcpx.utils.validation.subprocess.Popen")
    @patch("mcpx.utils.validation.validate_command_exists")
    def test_missing_result_and_error_fails(self, mock_validate, mock_popen):
        """Test that response without result or error returns failure."""
        mock_validate.return_value = None

        mock_process = MagicMock()
        mock_response = {"jsonrpc": "2.0", "id": 1}
        mock_process.communicate.return_value = (
            json.dumps(mock_response).encode("utf-8"),
            b""
        )
        mock_popen.return_value = mock_process

        server = MCPServer(
            name="incomplete-server",
            type="stdio",
            command="test-cmd"
        )
        success, message = health_check_stdio_server(server)

        assert success is False
        assert "missing 'result' or 'error' field" in message

    @patch("mcpx.utils.validation.subprocess.Popen")
    @patch("mcpx.utils.validation.validate_command_exists")
    def test_multiline_response_finds_json(self, mock_validate, mock_popen):
        """Test that JSON is found in multiline output."""
        mock_validate.return_value = None

        mock_process = MagicMock()
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "serverInfo": {"name": "multi-line-server", "version": "2.0.0"}
            }
        }
        # Simulate server outputting debug info before JSON
        output = f"Server starting...\nLoading config...\n{json.dumps(mock_response)}\n"
        mock_process.communicate.return_value = (output.encode("utf-8"), b"")
        mock_popen.return_value = mock_process

        server = MCPServer(
            name="multiline-server",
            type="stdio",
            command="test-cmd"
        )
        success, message = health_check_stdio_server(server)

        assert success is True
        assert "healthy" in message

    @patch("mcpx.utils.validation.subprocess.Popen")
    @patch("mcpx.utils.validation.validate_command_exists")
    def test_environment_variables_expanded(self, mock_validate, mock_popen):
        """Test that environment variables in server env are expanded."""
        mock_validate.return_value = None

        mock_process = MagicMock()
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"serverInfo": {"name": "env-server", "version": "1.0"}}
        }
        mock_process.communicate.return_value = (
            json.dumps(mock_response).encode("utf-8"),
            b""
        )
        mock_popen.return_value = mock_process

        server = MCPServer(
            name="env-server",
            type="stdio",
            command="test-cmd",
            env={"API_KEY": "${HOME}/key.txt"}
        )

        with patch.dict("os.environ", {"HOME": "/users/test"}):
            success, message = health_check_stdio_server(server)

        assert success is True
        # Check that env was passed to Popen
        call_kwargs = mock_popen.call_args[1]
        assert "env" in call_kwargs
        assert call_kwargs["env"]["API_KEY"] == "/users/test/key.txt"

    @patch("mcpx.utils.validation.subprocess.Popen")
    @patch("mcpx.utils.validation.validate_command_exists")
    def test_process_cleanup_on_success(self, mock_validate, mock_popen):
        """Test that process is terminated after successful check."""
        mock_validate.return_value = None

        mock_process = MagicMock()
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"serverInfo": {"name": "cleanup-server", "version": "1.0"}}
        }
        mock_process.communicate.return_value = (
            json.dumps(mock_response).encode("utf-8"),
            b""
        )
        mock_popen.return_value = mock_process

        server = MCPServer(
            name="cleanup-server",
            type="stdio",
            command="test-cmd"
        )
        health_check_stdio_server(server)

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called()

    @patch("mcpx.utils.validation.subprocess.Popen")
    @patch("mcpx.utils.validation.validate_command_exists")
    def test_process_kill_on_terminate_timeout(self, mock_validate, mock_popen):
        """Test that process is killed if terminate times out."""
        mock_validate.return_value = None

        mock_process = MagicMock()
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"serverInfo": {"name": "stubborn-server", "version": "1.0"}}
        }
        mock_process.communicate.return_value = (
            json.dumps(mock_response).encode("utf-8"),
            b""
        )
        # First wait (after terminate) times out, second wait (after kill) succeeds
        mock_process.wait.side_effect = [
            subprocess.TimeoutExpired(cmd=["test"], timeout=1),
            None
        ]
        mock_popen.return_value = mock_process

        server = MCPServer(
            name="stubborn-server",
            type="stdio",
            command="test-cmd"
        )
        health_check_stdio_server(server)

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    @patch("mcpx.utils.validation.subprocess.Popen")
    @patch("mcpx.utils.validation.validate_command_exists")
    def test_permission_error_handled(self, mock_validate, mock_popen):
        """Test that PermissionError is handled gracefully."""
        mock_validate.return_value = None
        mock_popen.side_effect = PermissionError("Permission denied")

        server = MCPServer(
            name="noperm-server",
            type="stdio",
            command="test-cmd"
        )
        success, message = health_check_stdio_server(server)

        assert success is False
        assert "permission denied" in message.lower()
        assert "noperm-server" in message

    @patch("mcpx.utils.validation.subprocess.Popen")
    @patch("mcpx.utils.validation.validate_command_exists")
    def test_os_error_handled(self, mock_validate, mock_popen):
        """Test that OSError is handled gracefully."""
        mock_validate.return_value = None
        mock_popen.side_effect = OSError("Resource temporarily unavailable")

        server = MCPServer(
            name="oserror-server",
            type="stdio",
            command="test-cmd"
        )
        success, message = health_check_stdio_server(server)

        assert success is False
        assert "OS error" in message
        assert "oserror-server" in message

    @patch("mcpx.utils.validation.subprocess.Popen")
    @patch("mcpx.utils.validation.validate_command_exists")
    def test_correct_init_request_sent(self, mock_validate, mock_popen):
        """Test that correct MCP initialize request is sent."""
        mock_validate.return_value = None

        mock_process = MagicMock()
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"serverInfo": {"name": "request-test", "version": "1.0"}}
        }
        mock_process.communicate.return_value = (
            json.dumps(mock_response).encode("utf-8"),
            b""
        )
        mock_popen.return_value = mock_process

        server = MCPServer(
            name="request-test",
            type="stdio",
            command="test-cmd",
            args=["--verbose"]
        )
        health_check_stdio_server(server)

        # Verify input sent to process
        call_args = mock_process.communicate.call_args
        input_bytes = call_args[1]["input"]
        input_str = input_bytes.decode("utf-8")
        request = json.loads(input_str.strip())

        assert request["jsonrpc"] == "2.0"
        assert request["id"] == 1
        assert request["method"] == "initialize"
        assert request["params"]["protocolVersion"] == MCP_PROTOCOL_VERSION
        assert request["params"]["clientInfo"]["name"] == MCP_CLIENT_NAME
        assert request["params"]["clientInfo"]["version"] == MCP_CLIENT_VERSION

    @patch("mcpx.utils.validation.subprocess.Popen")
    @patch("mcpx.utils.validation.validate_command_exists")
    def test_args_passed_to_command(self, mock_validate, mock_popen):
        """Test that server args are passed to command."""
        mock_validate.return_value = None

        mock_process = MagicMock()
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"serverInfo": {"name": "args-test", "version": "1.0"}}
        }
        mock_process.communicate.return_value = (
            json.dumps(mock_response).encode("utf-8"),
            b""
        )
        mock_popen.return_value = mock_process

        server = MCPServer(
            name="args-test",
            type="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"]
        )
        health_check_stdio_server(server)

        # Verify command and args passed to Popen
        call_args = mock_popen.call_args[0][0]
        assert call_args == ["npx", "-y", "@modelcontextprotocol/server-github"]


class TestHealthCheckConstants:
    """Tests for health check constants."""

    def test_protocol_version_format(self):
        """Test that protocol version is in expected format."""
        assert MCP_PROTOCOL_VERSION == "2024-11-05"

    def test_client_name(self):
        """Test that client name is set correctly."""
        assert MCP_CLIENT_NAME == "mcpx"

    def test_client_version(self):
        """Test that client version is set correctly."""
        assert MCP_CLIENT_VERSION == "0.1.0"

    def test_default_timeout(self):
        """Test that default timeout is 5 seconds."""
        assert HEALTH_CHECK_TIMEOUT == 5
