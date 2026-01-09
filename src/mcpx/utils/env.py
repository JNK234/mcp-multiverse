# Environment variable expansion utilities
import os
import re
import warnings

# ABOUTME: Pattern matches ${VAR_NAME} where VAR_NAME is uppercase with underscores
ENV_VAR_PATTERN = re.compile(r'\$\{([A-Z_][A-Z0-9_]*)\}')


def expand_env_vars(value: str) -> str:
    """Expand environment variables in ${VAR} format.

    ABOUTME: Supports ${VAR_NAME} syntax for environment variable expansion
    ABOUTME: Returns original value if variable not found (with warning)

    Args:
        value: String potentially containing ${VAR} references

    Returns:
        String with environment variables expanded

    Examples:
        >>> expand_env_vars("${HOME}/projects")
        '/Users/user/projects'
        >>> expand_env_vars("npx -y ${UNSET_VAR}")
        'npx -y ${UNSET_VAR}'  # with warning
    """
    def replace_var(match: re.Match[str]) -> str:
        var_name = match.group(1)
        if var_name in os.environ:
            return os.environ[var_name]
        else:
            warnings.warn(
                f"Environment variable '{var_name}' not found, keeping original",
                UserWarning,
                stacklevel=2
            )
            return match.group(0)

    return ENV_VAR_PATTERN.sub(replace_var, value)
