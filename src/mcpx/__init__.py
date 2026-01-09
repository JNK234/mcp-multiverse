# mcpx - Universal MCP Server Sync Manager
# ABOUTME: Version information
__version__ = "0.1.0"

# ABOUTME: Export core data models
# ABOUTME: Export config loading functions
from mcpx.config import ensure_config_dir, get_config_path, load_config
from mcpx.models import Config, MCPServer, PlatformAdapter

# ABOUTME: Export utility functions
from mcpx.utils import (
    ValidationError,
    create_backup,
    expand_env_vars,
    get_backup_dir,
    validate_command_exists,
    validate_server,
)

__all__ = [
    "__version__",
    "Config",
    "MCPServer",
    "PlatformAdapter",
    "ensure_config_dir",
    "get_config_path",
    "load_config",
    "expand_env_vars",
    "ValidationError",
    "validate_command_exists",
    "validate_server",
    "create_backup",
    "get_backup_dir",
]
