# ABOUTME: The generic engine — maps native config <-> canonical IR using tool descriptors.
# ABOUTME: import_mcp / export_mcp drive porting; mapping.py is the single mapping site.
from mcpx.engine.mcp_engine import ExportResult, export_mcp, import_mcp

__all__ = ["ExportResult", "export_mcp", "import_mcp"]
