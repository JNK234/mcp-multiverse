# Tests for environment variable expansion
import warnings

from mcpx.utils.env import ENV_VAR_PATTERN, expand_env_vars


def test_expand_single_env_var(monkeypatch):
    """Test expanding a single environment variable."""
    monkeypatch.setenv("HOME", "/home/user")

    result = expand_env_vars("${HOME}/projects")
    assert result == "/home/user/projects"


def test_expand_multiple_vars(monkeypatch):
    """Test expanding multiple variables in one string."""
    monkeypatch.setenv("HOME", "/home/user")
    monkeypatch.setenv("PROJECT", "myproject")

    result = expand_env_vars("${HOME}/${PROJECT}")
    assert result == "/home/user/myproject"


def test_expand_var_in_command(monkeypatch):
    """Test expanding variable in command context."""
    monkeypatch.setenv("NPM_TOKEN", "npm_12345")

    result = expand_env_vars("npx -y @scope/server --token=${NPM_TOKEN}")
    assert result == "npx -y @scope/server --token=npm_12345"


def test_expand_var_in_middle(monkeypatch):
    """Test expanding variable in middle of string."""
    monkeypatch.setenv("USER", "alice")

    result = expand_env_vars("/path/to/${USER}/files")
    assert result == "/path/to/alice/files"


def test_missing_var_returns_original(monkeypatch):
    """Test that missing variables are preserved with warning."""
    # Ensure variable is not set
    monkeypatch.delenv("MISSING_VAR", raising=False)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = expand_env_vars("command ${MISSING_VAR} arg")

        # Should return original string
        assert result == "command ${MISSING_VAR} arg"

        # Should have issued a warning
        assert len(w) == 1
        assert "MISSING_VAR" in str(w[0].message)
        assert "not found" in str(w[0].message)


def test_no_vars_in_string():
    """Test string without variables passes through unchanged."""
    result = expand_env_vars("npx -y server-name")
    assert result == "npx -y server-name"


def test_empty_string():
    """Test empty string handling."""
    result = expand_env_vars("")
    assert result == ""


def test_pattern_matches_valid_vars():
    """Test regex pattern matches valid variable names."""
    valid_cases = [
        "${HOME}",
        "${GITHUB_TOKEN}",
        "${API_KEY_123}",
        "${_PRIVATE_VAR}",
    ]

    for case in valid_cases:
        match = ENV_VAR_PATTERN.search(case)
        assert match is not None
        assert match.group(1) in ["HOME", "GITHUB_TOKEN", "API_KEY_123", "_PRIVATE_VAR"]


def test_pattern_rejects_invalid_vars():
    """Test regex pattern doesn't match invalid variable names."""
    invalid_cases = [
        "${lowercase}",
        "${MixedCase}",
        "${123NUM}",
        "${WITH-DASH}",
        "${WITH.DOT}",
    ]

    for case in invalid_cases:
        match = ENV_VAR_PATTERN.search(case)
        # Should either not match or not capture invalid name
        if match:
            # If it matched, ensure it didn't capture the invalid part
            assert match.group(1) != case[2:-1]  # Strip ${ and }


def test_nested_braces_not_supported():
    """Test that nested braces are not expanded."""
    result = expand_env_vars("${OUTER${INNER}}")
    # Pattern won't match nested braces
    assert result == "${OUTER${INNER}}"
