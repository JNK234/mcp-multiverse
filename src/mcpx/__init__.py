# ABOUTME: mcpx — port MCP servers across AI coding tools via a canonical IR.
# ABOUTME: Public surface: IR types, manifest IO, descriptor registry, port orchestration.
__version__ = "0.2.0"

from mcpx.descriptors import REGISTRY
from mcpx.ir import Manifest, MCPServerIR, Transport
from mcpx.manifest import get_manifest_path, load_manifest, save_manifest
from mcpx.port import import_to_manifest, installed_targets, port

__all__ = [
    "__version__",
    "MCPServerIR",
    "Manifest",
    "Transport",
    "REGISTRY",
    "get_manifest_path",
    "load_manifest",
    "save_manifest",
    "import_to_manifest",
    "installed_targets",
    "port",
]
