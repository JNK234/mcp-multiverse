# ABOUTME: Load/save the canonical IR hub at ~/.mcpx/manifest.json (replaces the old config.py).
# ABOUTME: Serializes MCPServerIR <-> JSON; this is the authoritative, human-editable server set.
from __future__ import annotations

from pathlib import Path
from typing import Any

from mcpx.ir import Manifest, MCPServerIR, Transport

MANIFEST_VERSION = "2.0"

CONFIG_DIR = Path.home() / ".mcpx"
MANIFEST_FILE = CONFIG_DIR / "manifest.json"


def get_manifest_path() -> Path:
    """Return the path to the manifest file (~/.mcpx/manifest.json)."""
    return MANIFEST_FILE


def ensure_config_dir() -> Path:
    """Create ~/.mcpx/ if missing and return it."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def server_to_dict(server: MCPServerIR) -> dict[str, Any]:
    """Serialize one MCPServerIR to a JSON-friendly dict (omitting empty fields).

    ABOUTME: transport stored as its string value; only set/non-empty fields are written.
    """
    data: dict[str, Any] = {"transport": server.transport.value}
    if server.command is not None:
        data["command"] = server.command
    if server.args:
        data["args"] = list(server.args)
    if server.env:
        data["env"] = dict(server.env)
    if server.url is not None:
        data["url"] = server.url
    if server.headers:
        data["headers"] = dict(server.headers)
    if server.bearer_token_env_var is not None:
        data["bearer_token_env_var"] = server.bearer_token_env_var
    if server.disabled:
        data["disabled"] = True
    if server.auto_approve:
        data["auto_approve"] = list(server.auto_approve)
    if server.extra:
        data["extra"] = {k: dict(v) for k, v in server.extra.items()}
    return data


def server_from_dict(name: str, data: dict[str, Any]) -> MCPServerIR:
    """Deserialize one IR server dict back into an MCPServerIR.

    ABOUTME: Infers transport from the stored value, defaulting to http if a url is present.
    """
    transport_raw = data.get("transport")
    if transport_raw:
        transport = Transport(transport_raw)
    elif data.get("url"):
        transport = Transport.HTTP
    else:
        transport = Transport.STDIO

    return MCPServerIR(
        name=name,
        transport=transport,
        command=data.get("command"),
        args=list(data.get("args", [])),
        env=dict(data.get("env", {})),
        url=data.get("url"),
        headers=dict(data.get("headers", {})),
        bearer_token_env_var=data.get("bearer_token_env_var"),
        disabled=bool(data.get("disabled", False)),
        auto_approve=list(data.get("auto_approve", [])),
        extra={k: dict(v) for k, v in data.get("extra", {}).items()},
    )


def load_manifest(path: Path | None = None) -> Manifest:
    """Load the IR manifest from disk.

    ABOUTME: Returns an empty Manifest if the file doesn't exist.
    ABOUTME: Uses the json codec so it benefits from consistent IO behavior.
    """
    from mcpx.codecs import codec_for

    path = path or get_manifest_path()
    if not path.exists():
        return Manifest(version=MANIFEST_VERSION)

    raw = codec_for("json").read(path)
    version = raw.get("mcpx", {}).get("version", MANIFEST_VERSION)
    servers_raw = raw.get("servers", {})
    servers = {name: server_from_dict(name, sd) for name, sd in servers_raw.items()}
    return Manifest(version=version, servers=servers)


def save_manifest(manifest: Manifest, path: Path | None = None) -> None:
    """Persist the IR manifest to disk.

    ABOUTME: Writes {"mcpx": {"version"}, "servers": {...}} via the json codec.
    """
    from mcpx.codecs import codec_for

    path = path or get_manifest_path()
    data: dict[str, Any] = {
        "mcpx": {"version": manifest.version},
        "servers": {name: server_to_dict(s) for name, s in manifest.servers.items()},
    }
    codec_for("json").write(path, data)
