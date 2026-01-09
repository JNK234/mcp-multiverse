# Tests for validation utilities
import os

import pytest

from mcpx.models import MCPServer
from mcpx.utils.validation import ValidationError, validate_command_exists, validate_server


class TestValidateCommandExists:
    """Tests for validate_command_exists function."""

    def test_valid_command_returns_none(self):
        """Test that existing command returns None."""
        # Use 'python' which should always exist
        result = validate_command_exists("python")
        assert result is None

    def test_invalid_command_returns_error(self):
        """Test that non-existent command returns ValidationError."""
        result = validate_command_exists("definitely_not_a_real_command_xyz123")
        assert result is not None
        assert result.severity == "error"
        assert "not found" in result.message.lower()
        assert "definitely_not_a_real_command_xyz123" in result.message

    def test_error_has_empty_server_name(self):
        """Test that command validation error has empty server_name."""
        result = validate_command_exists("nonexistent_cmd")
        assert result is not None
        assert result.server_name == ""


class TestValidateServer:
    """Tests for validate_server function."""

    def test_valid_server_passes(self):
        """Test that server with valid command passes validation."""
        server = MCPServer(
            name="test-server",
            command="python",
            args=["-m", "module"]
        )
        errors = validate_server(server)
        assert errors == []

    def test_missing_command_fails(self):
        """Test that server with missing command fails validation."""
        server = MCPServer(
            name="broken-server",
            command="nonexistent_command_xyz"
        )
        errors = validate_server(server)
        assert len(errors) == 1
        assert errors[0].severity == "error"
        assert errors[0].server_name == "broken-server"
        assert "not found" in errors[0].message.lower()

    def test_unset_env_var_in_command_warns(self):
        """Test that unset env var in command generates warning."""
        # Ensure the var is not set - use uppercase for regex match
        var_name = "MCPX_TEST_UNSET_VAR"
        if var_name in os.environ:
            del os.environ[var_name]

        server = MCPServer(
            name="test-server",
            command="python",
            args=["${MCPX_TEST_UNSET_VAR}/script.py"]
        )
        errors = validate_server(server)
        assert len(errors) == 1
        assert errors[0].severity == "warning"
        assert "MCPX_TEST_UNSET_VAR" in errors[0].message
        assert "args" in errors[0].message

    def test_set_env_var_no_warning(self):
        """Test that set env var does not generate warning."""
        # Set a test variable
        os.environ["MCPX_TEST_SET_VAR"] = "/test/path"

        server = MCPServer(
            name="test-server",
            command="python",
            args=["${MCPX_TEST_SET_VAR}/script.py"]
        )
        errors = validate_server(server)
        # Should only have the command validation, no env var warnings
        assert all("MCPX_TEST_SET_VAR" not in err.message for err in errors)

        # Cleanup
        del os.environ["MCPX_TEST_SET_VAR"]

    def test_unset_env_var_in_env_dict_warns(self):
        """Test that unset env var in env dict generates warning."""
        var_name = "MCPX_TEST_DICT_VAR"
        if var_name in os.environ:
            del os.environ[var_name]

        server = MCPServer(
            name="test-server",
            command="python",
            env={"API_KEY": "${MCPX_TEST_DICT_VAR}"}
        )
        errors = validate_server(server)
        assert len(errors) == 1
        assert errors[0].severity == "warning"
        assert "MCPX_TEST_DICT_VAR" in errors[0].message
        assert "env.API_KEY" in errors[0].message

    def test_multiple_env_vars_all_warned(self):
        """Test that multiple unset env vars all generate warnings."""
        var1 = "MCPX_TEST_VAR1"
        var2 = "MCPX_TEST_VAR2"
        for v in [var1, var2]:
            if v in os.environ:
                del os.environ[v]

        server = MCPServer(
            name="test-server",
            command="python",
            args=["${MCPX_TEST_VAR1}", "${MCPX_TEST_VAR2}"]
        )
        errors = validate_server(server)
        assert len(errors) == 2
        messages = {err.message for err in errors}
        assert any("MCPX_TEST_VAR1" in msg for msg in messages)
        assert any("MCPX_TEST_VAR2" in msg for msg in messages)

    def test_valid_server_with_args_and_env(self):
        """Test valid server with both args and env passes."""
        os.environ["MCPX_TEST_VALID_VAR"] = "/valid/path"

        server = MCPServer(
            name="valid-server",
            command="python",
            args=["-m", "module", "${MCPX_TEST_VALID_VAR}"],
            env={"TEST": "value"}
        )
        errors = validate_server(server)
        # Should not have any errors about the set variable
        assert not any("MCPX_TEST_VALID_VAR" in err.message for err in errors)

        # Cleanup
        del os.environ["MCPX_TEST_VALID_VAR"]


class TestValidationError:
    """Tests for ValidationError dataclass."""

    def test_validation_error_properties(self):
        """Test that ValidationError has correct properties."""
        error = ValidationError(
            server_name="test-server",
            message="Test error message",
            severity="error"
        )
        assert error.server_name == "test-server"
        assert error.message == "Test error message"
        assert error.severity == "error"

    def test_validation_error_is_immutable(self):
        """Test that ValidationError is frozen (immutable)."""
        from dataclasses import FrozenInstanceError

        error = ValidationError(
            server_name="test",
            message="msg",
            severity="warning"
        )
        with pytest.raises(FrozenInstanceError):
            error.server_name = "modified"  # type: ignore[attr-defined]

    def test_error_severity(self):
        """Test error severity type."""
        error = ValidationError(
            server_name="test",
            message="Critical error",
            severity="error"
        )
        assert error.severity == "error"

    def test_warning_severity(self):
        """Test warning severity type."""
        error = ValidationError(
            server_name="test",
            message="Minor issue",
            severity="warning"
        )
        assert error.severity == "warning"
