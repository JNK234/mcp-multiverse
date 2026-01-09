# ABOUTME: Validation utilities for MCP server configurations
# ABOUTME: Includes health check functionality for stdio MCP servers
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from urllib.parse import urlparse

from mcpx.models import MCPServer

# MCP protocol constants
MCP_PROTOCOL_VERSION = "2024-11-05"
MCP_CLIENT_NAME = "mcpx"
MCP_CLIENT_VERSION = "0.1.0"
HEALTH_CHECK_TIMEOUT = 5  # seconds


@dataclass(frozen=True)
class ValidationError:
    """Represents a validation error or warning.

    ABOUTME: Uses frozen dataclass for immutability
    ABOUTME: Severity level distinguishes between blocking errors and warnings
    """
    server_name: str
    message: str
    severity: str  # 'error' or 'warning'


def validate_command_exists(command: str) -> ValidationError | None:
    """Validate that a command exists on the system.

    ABOUTME: Uses shutil.which() for cross-platform command lookup
    ABOUTME: Returns None if command found, ValidationError otherwise

    Args:
        command: Command name or path to check

    Returns:
        ValidationError if command not found, None otherwise

    Examples:
        >>> validate_command_exists("npx")
        None
        >>> validate_command_exists("nonexistent_cmd")
        ValidationError(
        ...     server_name='',
        ...     message='Command not found: nonexistent_cmd',
        ...     severity='error'
        ... )
    """
    if shutil.which(command) is None:
        return ValidationError(
            server_name="",
            message=f"Command not found: {command}",
            severity="error"
        )
    return None


def validate_url(url: str) -> ValidationError | None:
    """Validate that a URL is properly formatted.

    ABOUTME: Uses urllib.parse for URL parsing
    ABOUTME: Requires HTTP or HTTPS scheme
    ABOUTME: Returns None if URL valid, ValidationError otherwise

    Args:
        url: URL string to validate

    Returns:
        ValidationError if URL invalid, None otherwise
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return ValidationError(
                server_name="",
                message=f"URL must use HTTP or HTTPS scheme: {url}",
                severity="error"
            )
        if not parsed.netloc:
            return ValidationError(
                server_name="",
                message=f"URL missing host/domain: {url}",
                severity="error"
            )
    except Exception as e:
        return ValidationError(
            server_name="",
            message=f"Invalid URL format '{url}': {e}",
            severity="error"
        )
    return None


def validate_server(server: MCPServer) -> list[ValidationError]:
    """Validate an MCP server configuration.

    ABOUTME: Checks server type and validates accordingly
    ABOUTME: For stdio: checks command existence and environment variables
    ABOUTME: For http: checks URL format and headers
    ABOUTME: Warns about unset environment variables
    ABOUTME: Returns list of all validation errors/warnings

    Args:
        server: MCPServer instance to validate

    Returns:
        List of ValidationError instances (empty if valid)

    Examples:
        >>> server = MCPServer(name="test", type="stdio", command="npx", args=["-y", "server"])
        >>> validate_server(server)
        []
        >>> server = MCPServer(name="http_test", type="http", url="https://api.example.com/mcp")
        >>> validate_server(server)
        []
    """
    errors: list[ValidationError] = []

    if server.type == "stdio":
        # Validate command exists for stdio servers
        if server.command:
            cmd_error = validate_command_exists(server.command)
            if cmd_error:
                errors.append(ValidationError(
                    server_name=server.name,
                    message=cmd_error.message,
                    severity=cmd_error.severity
                ))

            # Check for environment variables in command
            if server.command:
                for match in re.finditer(r'\$\{([A-Z_][A-Z0-9_]*)\}', server.command):
                    var_name = match.group(1)
                    if var_name not in os.environ:
                        errors.append(ValidationError(
                            server_name=server.name,
                            message=f"Environment variable '${var_name}' not set (referenced in command)",
                            severity="warning"
                        ))

            # Check in args
            for arg in server.args:
                for match in re.finditer(r'\$\{([A-Z_][A-Z0-9_]*)\}', arg):
                    var_name = match.group(1)
                    if var_name not in os.environ:
                        errors.append(ValidationError(
                            server_name=server.name,
                            message=f"Environment variable '${var_name}' not set (referenced in args)",
                            severity="warning"
                        ))

            # Check in env values
            for key, value in server.env.items():
                for match in re.finditer(r'\$\{([A-Z_][A-Z0-9_]*)\}', value):
                    var_name = match.group(1)
                    if var_name not in os.environ:
                        errors.append(ValidationError(
                            server_name=server.name,
                            message=f"Environment variable '${var_name}' not set (referenced in env.{key})",
                            severity="warning"
                        ))

    elif server.type == "http":
        # Validate URL format for HTTP servers
        if server.url:
            url_error = validate_url(server.url)
            if url_error:
                errors.append(ValidationError(
                    server_name=server.name,
                    message=url_error.message,
                    severity=url_error.severity
                ))

            # Check for environment variables in URL
            if server.url:
                for match in re.finditer(r'\$\{([A-Z_][A-Z0-9_]*)\}', server.url):
                    var_name = match.group(1)
                    if var_name not in os.environ:
                        errors.append(ValidationError(
                            server_name=server.name,
                            message=f"Environment variable '${var_name}' not set (referenced in url)",
                            severity="warning"
                        ))

            # Check for environment variables in headers
            for key, value in server.headers.items():
                for match in re.finditer(r'\$\{([A-Z_][A-Z0-9_]*)\}', value):
                    var_name = match.group(1)
                    if var_name not in os.environ:
                        errors.append(ValidationError(
                            server_name=server.name,
                            message=f"Environment variable '${var_name}' not set (referenced in headers.{key})",
                            severity="warning"
                        ))

    return errors


def health_check_stdio_server(server: MCPServer, timeout: int | None = None) -> tuple[bool, str]:
    """Perform health check on a stdio MCP server.

    ABOUTME: Validates stdio server by starting it and sending MCP initialize request
    ABOUTME: Returns tuple of (success, message) indicating health status

    This function:
    1. Verifies command exists in PATH
    2. Verifies referenced environment variables exist (warnings only)
    3. Attempts to start server subprocess
    4. Sends MCP initialize request (JSON-RPC format)
    5. Waits for response up to timeout seconds
    6. Cleans up subprocess on completion or timeout

    Args:
        server: MCPServer instance to health check (must be stdio type)
        timeout: Timeout in seconds (default: HEALTH_CHECK_TIMEOUT)

    Returns:
        Tuple of (success: bool, message: str)
        - success: True if server responded to initialization
        - message: Description of result or error

    Examples:
        >>> server = MCPServer(name="test", type="stdio", command="echo", args=["{}"])
        >>> success, msg = health_check_stdio_server(server)
    """
    if timeout is None:
        timeout = HEALTH_CHECK_TIMEOUT

    # Validate server type
    if server.type != "stdio":
        return False, f"Server '{server.name}' is not a stdio server (type: {server.type})"

    # Check command exists
    if not server.command:
        return False, f"Server '{server.name}' has no command specified"

    cmd_error = validate_command_exists(server.command)
    if cmd_error:
        return False, f"Server '{server.name}': {cmd_error.message}"

    # Build command line
    cmd = [server.command] + list(server.args)

    # Build environment with server's env vars expanded
    env = os.environ.copy()
    for key, value in server.env.items():
        # Expand environment variable references in values
        expanded_value = value
        for match in re.finditer(r'\$\{([A-Z_][A-Z0-9_]*)\}', value):
            var_name = match.group(1)
            env_value = os.environ.get(var_name, "")
            expanded_value = expanded_value.replace(f"${{{var_name}}}", env_value)
        env[key] = expanded_value

    # Create MCP initialize request
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {
                "name": MCP_CLIENT_NAME,
                "version": MCP_CLIENT_VERSION
            }
        }
    }

    process: subprocess.Popen[bytes] | None = None
    try:
        # Start the server process
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )

        # Send initialize request
        request_json = json.dumps(init_request) + "\n"
        stdout_data, stderr_data = process.communicate(
            input=request_json.encode("utf-8"),
            timeout=timeout
        )

        # Parse response
        stdout_str = stdout_data.decode("utf-8").strip()
        if not stdout_str:
            stderr_str = stderr_data.decode("utf-8").strip()
            if stderr_str:
                return False, f"Server '{server.name}' returned no response. stderr: {stderr_str[:200]}"
            return False, f"Server '{server.name}' returned no response"

        # MCP servers may output multiple lines; find the JSON response
        response_line = None
        for line in stdout_str.split("\n"):
            line = line.strip()
            if line.startswith("{"):
                response_line = line
                break

        if not response_line:
            return False, f"Server '{server.name}' returned non-JSON response: {stdout_str[:200]}"

        try:
            response = json.loads(response_line)
        except json.JSONDecodeError as e:
            return False, f"Server '{server.name}' returned invalid JSON: {e}"

        # Validate JSON-RPC response
        if "jsonrpc" not in response:
            return False, f"Server '{server.name}' response missing 'jsonrpc' field"

        if response.get("jsonrpc") != "2.0":
            return False, f"Server '{server.name}' has invalid JSON-RPC version: {response.get('jsonrpc')}"

        # Check for error response
        if "error" in response:
            error = response["error"]
            error_msg = error.get("message", str(error))
            return False, f"Server '{server.name}' returned error: {error_msg}"

        # Check for result (successful initialization)
        if "result" in response:
            result = response["result"]
            # Extract server info if available
            server_info = result.get("serverInfo", {})
            server_name_resp = server_info.get("name", "unknown")
            server_version = server_info.get("version", "unknown")
            return True, f"Server '{server.name}' healthy (server: {server_name_resp} v{server_version})"

        return False, f"Server '{server.name}' response missing 'result' or 'error' field"

    except subprocess.TimeoutExpired:
        return False, f"Server '{server.name}' timed out after {timeout} seconds"
    except FileNotFoundError:
        return False, f"Server '{server.name}': command not found: {server.command}"
    except PermissionError:
        return False, f"Server '{server.name}': permission denied executing: {server.command}"
    except OSError as e:
        return False, f"Server '{server.name}': OS error: {e}"
    finally:
        # Clean up subprocess
        if process is not None:
            try:
                process.terminate()
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            except Exception:
                pass  # Best effort cleanup
