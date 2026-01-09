# Sync orchestration for mcpx
from dataclasses import dataclass, field

from mcpx.config import ensure_config_dir, get_config_path
from mcpx.models import Config, MCPServer
from mcpx.platforms import get_all_platforms
from mcpx.utils import create_backup, get_backup_dir, validate_server


@dataclass
class SyncReport:
    """Report from sync operation.

    ABOUTME: Tracks success/failure across platforms
    ABOUTME: Contains per-platform server counts and any errors
    """
    platforms_synced: int
    platforms_total: int
    servers_synced: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def add_platform_result(self, platform_name: str, count: int) -> None:
        """Record sync result for a platform.

        ABOUTME: Increments synced count if count > 0
        ABOUTME: Always records server count
        """
        if count > 0:
            self.platforms_synced += 1
        self.servers_synced[platform_name] = count

    def add_error(self, error: str) -> None:
        """Record an error that occurred during sync.

        ABOUTME: Errors are non-fatal, sync continues
        """
        self.errors.append(error)


@dataclass
class FirstRunReport:
    """Report from first-run initialization.

    ABOUTME: Tracks discovered servers from all platforms
    ABOUTME: Contains deduplicated server count
    """
    server_count: int
    platforms_scanned: dict[str, int] = field(default_factory=dict)


def merge_servers(
    managed: dict[str, MCPServer],
    existing: dict[str, MCPServer]
) -> dict[str, MCPServer]:
    """Merge managed servers with existing orphans.

    ABOUTME: Preserves existing servers not in managed set (orphans)
    ABOUTME: Managed servers override existing ones with same name
    ABOUTME: Returns new dict (doesn't mutate inputs)

    Args:
        managed: Servers from mcpx config (source of truth)
        existing: Servers currently in platform config

    Returns:
        Merged dict with managed + orphan servers

    Examples:
        >>> managed = {"a": MCPServer(name="a", command="npx")}
        >>> existing = {
        ...     "a": MCPServer(name="a", command="old"),
        ...     "b": MCPServer(name="b", command="npx")
        ... }
        >>> merged = merge_servers(managed, existing)
        >>> set(merged.keys()) == {"a", "b"}
        True
        >>> merged["a"].command == "npx"
        True
        >>> merged["b"].command == "npx"
        True
    """
    # Start with managed servers (source of truth)
    result: dict[str, MCPServer] = dict(managed)

    # Add orphans (servers in existing but not in managed)
    orphan_names = set(existing.keys()) - set(managed.keys())
    for name in orphan_names:
        result[name] = existing[name]

    return result


def sync_all(config: Config) -> SyncReport:
    """Sync config to all platform adapters.

    ABOUTME: Validates servers, creates backups, merges with orphans, saves
    ABOUTME: Continues on platform errors, records them in report
    ABOUTME: Returns detailed report of sync operation

    Args:
        config: Loaded mcpx configuration

    Returns:
        SyncReport with results from all platforms

    Examples:
        >>> from mcpx.config import load_config, get_config_path
        >>> config = load_config(get_config_path())
        >>> report = sync_all(config)
        >>> print(f"Synced {report.platforms_synced}/{report.platforms_total} platforms")
        Synced 2/2 platforms
    """
    platforms = get_all_platforms()
    report = SyncReport(platforms_synced=0, platforms_total=len(platforms))

    # Validate all servers first (fail-fast on config errors)
    validation_errors: list[str] = []
    for server_name, server in config.servers.items():
        errors = validate_server(server)
        for err in errors:
            if err.severity == "error":
                validation_errors.append(f"Server '{server_name}': {err.message}")

    if validation_errors:
        # Add all validation errors to report
        for error_msg in validation_errors:
            report.add_error(error_msg)
        # Return early - don't sync if config has errors
        return report

    # Sync to each platform
    for platform in platforms:
        try:
            # Skip platform if config path doesn't exist
            if platform.config_path is None:
                report.add_error(
                    f"{platform.name}: config path not found (platform not installed?)"
                )
                report.add_platform_result(platform.name, 0)
                continue

            # Create backup
            backup_dir = get_backup_dir()
            create_backup(platform.config_path, backup_dir)

            # Load existing servers
            existing = platform.load()

            # Merge managed servers with orphans
            merged = merge_servers(config.servers, existing)

            # Save merged config
            platform.save(merged)

            # Record success
            report.add_platform_result(platform.name, len(merged))

        except Exception as e:
            # Record error but continue with other platforms
            report.add_error(f"{platform.name}: {e}")
            report.add_platform_result(platform.name, 0)

    return report


def first_run_init() -> FirstRunReport:
    """Auto-detect and generate config from existing platform configurations.

    ABOUTME: Scans all platforms for existing MCP servers
    ABOUTME: Deduplicates servers by name
    ABOUTME: Generates ~/.mcpx/config.json
    ABOUTME: Returns report with discovered server count

    Returns:
        FirstRunReport with server count and platforms scanned

    Examples:
        >>> report = first_run_init()
        >>> print(f"Found {report.server_count} servers")
        Found 5 servers
    """
    import json

    # Create ~/.mcpx/ directory
    ensure_config_dir()

    # Get all platforms
    platforms = get_all_platforms()

    # Collect all servers from all platforms
    all_servers: dict[str, MCPServer] = {}
    platforms_scanned: dict[str, int] = {}

    for platform in platforms:
        try:
            if platform.config_path is None:
                continue

            servers = platform.load()
            if servers:
                # Add servers (later platforms override earlier ones if names conflict)
                all_servers.update(servers)
                platforms_scanned[platform.name] = len(servers)

        except Exception:
            # Skip platforms that can't be read
            continue

    # Generate config.json
    config_path = get_config_path()

    # Build JSON config
    config_data = {
        "mcpx": {
            "version": "1.0"
        },
        "servers": {}
    }

    for server_name, server in all_servers.items():
        server_data = {
            "type": server.type
        }

        if server.type == "stdio":
            if server.command:
                server_data["command"] = server.command
            if server.args:
                server_data["args"] = server.args
            if server.env:
                server_data["env"] = server.env
        elif server.type == "http":
            if server.url:
                server_data["url"] = server.url
            if server.headers:
                server_data["headers"] = server.headers

        config_data["servers"][server_name] = server_data

    # Write config file
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)
        f.write("\n")

    return FirstRunReport(
        server_count=len(all_servers),
        platforms_scanned=platforms_scanned
    )
