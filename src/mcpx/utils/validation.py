# Validation utilities for MCP server configurations
import os
import re
import shutil
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from mcpx.models import MCPServer

if TYPE_CHECKING:
    pass


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
