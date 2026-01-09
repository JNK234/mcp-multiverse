# mcpx - Universal MCP Server Sync Manager

## Specification Document

**Version:** 1.0.0-draft
**Created:** 2026-01-08
**Status:** MVP Specification

---

## 1. Executive Summary

**mcpx** is a CLI tool that synchronizes MCP (Model Context Protocol) server configurations across multiple AI coding assistants from a single source of truth. It eliminates config drift, format translation, and maintenance overhead when using multiple AI tools.

### Core Problem

Developers using multiple AI coding assistants (Claude Code, Gemini CLI, Codex CLI, Roo Code, Kilo Code, Cline) must manually maintain MCP configurations in different files, formats (JSON/TOML), and field names. This leads to:

- **Config drift**: Platforms get out of sync when manually editing
- **Format differences**: JSON vs TOML, camelCase vs snake_case
- **Path/command validation**: MCPs break when paths change
- **Maintenance overhead**: 6 files to update for every MCP change

### Solution

A single TOML config file (`~/.mcpx/config.toml`) that defines all MCP servers once, with automatic sync to all supported platforms.

---

## 2. Requirements Summary

| Requirement | Decision |
|-------------|----------|
| **Sync Model** | Declarative source of truth |
| **Distribution** | CLI tool only (`pip install mcpx`) |
| **Config Location** | `~/.mcpx/config.toml` |
| **Config Format** | TOML |
| **Python Version** | 3.12+ |
| **Field Strategy** | Strict common subset (portable fields only) |
| **Error Handling** | Error and skip invalid MCPs, continue sync |
| **Orphan Policy** | Preserve platform-native MCPs not in source |
| **Env Vars** | `${VAR}` syntax expansion at sync time |
| **Backups** | Automatic timestamped backups |
| **Output** | Verbose by default |
| **Filtering** | All or nothing for global sync |
| **Init Flow** | Auto-detect on first run |
| **Project-Level** | `mcpx init` for interactive subset selection per project |

---

## 3. Supported Platforms

### 3.1 Platform Configuration Matrix

| Platform | Config Path | Format | Key Name | Notes |
|----------|-------------|--------|----------|-------|
| **Claude Code** | `~/.claude.json` | JSON | `mcpServers` | Project-level in file |
| **Gemini CLI** | `~/.gemini/settings.json` | JSON | `mcpServers` | Part of larger settings |
| **Codex CLI** | `~/.codex/config.toml` | TOML | `mcp_servers` | snake_case keys |
| **Roo Code** | VS Code globalStorage | JSON | `mcpServers` | See paths below |
| **Kilo Code** | VS Code globalStorage | JSON | `mcpServers` | See paths below |
| **Cline** | VS Code globalStorage | JSON | `mcpServers` | See paths below |

### 3.2 VS Code Extension Paths

#### Cline (`saoudrizwan.claude-dev`)

| OS | Path |
|----|------|
| macOS | `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json` |
| Linux | `~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json` |
| Windows | `%APPDATA%/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json` |

#### Roo Code (`rooveterinaryinc.roo-cline`)

| OS | Path |
|----|------|
| macOS | `~/Library/Application Support/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json` |
| Linux | `~/.config/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json` |
| Windows | `%APPDATA%/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json` |

#### Kilo Code (`kilocode.kilocode`)

| OS | Path |
|----|------|
| macOS | `~/Library/Application Support/Code/User/globalStorage/kilocode.kilocode/settings/mcp_settings.json` |
| Linux | `~/.config/Code/User/globalStorage/kilocode.kilocode/settings/mcp_settings.json` |
| Windows | `%APPDATA%/Code/User/globalStorage/kilocode.kilocode/settings/mcp_settings.json` |

---

## 4. Configuration Schema

### 4.1 mcpx Config Location

```
~/.mcpx/
├── config.toml          # Source of truth
├── backups/             # Timestamped backups
│   ├── claude_20260108_143022.json
│   ├── gemini_20260108_143022.json
│   └── ...
└── mcpx.log             # Operation logs
```

### 4.2 Config Format (TOML)

```toml
# ~/.mcpx/config.toml
# mcpx configuration - source of truth for all MCP servers

[mcpx]
version = "1.0"

# MCP Server Definitions
# Each server uses the common subset of fields portable across all platforms

[servers.filesystem]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "${HOME}/projects"]
env = { }

[servers.github]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { GITHUB_PERSONAL_ACCESS_TOKEN = "${GITHUB_TOKEN}" }

[servers.memory]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-memory"]

[servers.context7]
command = "npx"
args = ["-y", "@upstash/context7-mcp@latest"]

[servers.sequential-thinking]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-sequential-thinking"]
```

### 4.3 Common Subset Fields

These fields are portable across ALL supported platforms:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `command` | string | Yes | Executable to run (e.g., `npx`, `python`, `node`) |
| `args` | array[string] | No | Command-line arguments |
| `env` | table | No | Environment variables (supports `${VAR}` expansion) |

**Explicitly NOT included** (platform-specific, would break portability):

- `disabled` / `enabled` - Manage via platform UI
- `timeout` / `tool_timeout_sec` - Platform defaults vary
- `autoApprove` / `alwaysAllow` - Security setting, per-platform
- `transportType` / `type` - Auto-detected from command vs url
- `url` / `httpUrl` - Remote servers require platform-specific auth
- `headers` - Auth is platform-specific
- `trust` / `includeTools` / `excludeTools` - Per-platform preferences

---

## 5. CLI Interface

### 5.1 Commands

```bash
# Primary command - sync global config to all platforms
mcpx sync

# Initialize project-level config (interactive selection)
mcpx init

# List all MCPs in source config
mcpx list

# Validate config without syncing
mcpx validate

# Show version
mcpx --version
mcpx -V

# Help
mcpx --help
mcpx -h
```

### 5.2 Command Details

#### `mcpx sync`

Reads `~/.mcpx/config.toml` and writes to all platform configs.

**Behavior:**
1. Load and parse source config
2. Validate each MCP (command exists on system)
3. For each platform:
   a. Create backup to `~/.mcpx/backups/`
   b. Load existing platform config
   c. Merge MCPs (preserve orphans, update/add managed ones)
   d. Write updated config
4. Report results

**Output (verbose by default):**
```
mcpx sync v1.0.0
Loading config from ~/.mcpx/config.toml
Found 5 MCP servers: filesystem, github, memory, context7, sequential-thinking

Validating commands...
  ✓ npx found at /usr/local/bin/npx

Syncing to platforms...
  ✓ Claude Code (~/.claude.json) - backed up, 5 servers synced
  ✓ Gemini CLI (~/.gemini/settings.json) - backed up, 5 servers synced
  ✓ Codex CLI (~/.codex/config.toml) - backed up, 5 servers synced
  ✓ Roo Code - backed up, 5 servers synced
  ✓ Kilo Code - backed up, 5 servers synced
  ✓ Cline - backed up, 5 servers synced

Sync complete: 6/6 platforms updated
```

**Error Handling:**
```
mcpx sync v1.0.0
Loading config from ~/.mcpx/config.toml
Found 5 MCP servers

Validating commands...
  ✗ Server 'broken-mcp': command 'nonexistent' not found - SKIPPING

Syncing to platforms...
  ✓ Claude Code - 4 servers synced (1 skipped)
  ✗ Roo Code - config path not found (VS Code not installed?)
  ...

Sync complete: 5/6 platforms updated, 1 failed
```

#### `mcpx list`

Lists all MCPs defined in source config.

**Output:**
```
mcpx list v1.0.0

MCP Servers in ~/.mcpx/config.toml:

  filesystem
    command: npx
    args: -y @modelcontextprotocol/server-filesystem /Users/user/projects

  github
    command: npx
    args: -y @modelcontextprotocol/server-github
    env: GITHUB_PERSONAL_ACCESS_TOKEN=${GITHUB_TOKEN}

  memory
    command: npx
    args: -y @modelcontextprotocol/server-memory

Total: 3 servers
```

#### `mcpx validate`

Validates config without modifying any files.

**Checks:**
1. TOML syntax valid
2. Required fields present (`command`)
3. Commands exist on system (`which`/`where`)
4. Environment variables referenced exist

**Output:**
```
mcpx validate v1.0.0

Validating ~/.mcpx/config.toml...

  ✓ TOML syntax valid
  ✓ 5 servers defined

  Checking commands:
    ✓ npx -> /usr/local/bin/npx

  Checking environment variables:
    ✓ ${HOME} -> /Users/user
    ⚠ ${GITHUB_TOKEN} not set (server: github)

Validation complete: 0 errors, 1 warning
```

#### `mcpx init`

Initializes project-level MCP configuration with interactive selection.

**Behavior:**
1. Check if `.mcpx.toml` already exists in current directory
2. Load global config from `~/.mcpx/config.toml`
3. Present interactive selection of available MCPs
4. Write selected MCPs to `.mcpx.toml`
5. Sync to platforms that support project-level configs

**Output:**
```
mcpx init v1.0.0

Loading global MCPs from ~/.mcpx/config.toml...
Found 8 servers available.

Select MCPs to enable for this project:
  [x] filesystem     - File system access
  [x] github         - GitHub integration
  [ ] memory         - Persistent memory
  [x] context7       - Documentation lookup
  [ ] sequential-thinking
  [ ] perplexity
  [ ] playwright
  [ ] chrome-devtools

Use arrow keys to navigate, space to toggle, enter to confirm.

Creating .mcpx.toml with 3 servers...

Syncing to project-level configs...
  ✓ Claude Code (.mcp.json) - 3 servers
  ✓ Roo Code (.roo/mcp.json) - 3 servers
  ✓ Kilo Code (.kilocode/mcp.json) - 3 servers
  ⊘ Gemini CLI - no project-level support
  ⊘ Codex CLI - no project-level support
  ⊘ Cline - no project-level support

Project initialized! Run 'mcpx init' again to modify selection.
```

**Project Config Format (`.mcpx.toml`):**
```toml
# Project-level MCP configuration
# Generated by mcpx init - edit or re-run 'mcpx init' to modify

[mcpx]
version = "1.0"

# Selected MCPs from global config (by name)
servers = ["filesystem", "github", "context7"]
```

**Platforms with Project-Level Support:**

| Platform | Project Config Path | Notes |
|----------|---------------------|-------|
| Claude Code | `.mcp.json` | Official project-level config |
| Roo Code | `.roo/mcp.json` | Project-level override |
| Kilo Code | `.kilocode/mcp.json` | Project-level override |
| Gemini CLI | ❌ | Global only |
| Codex CLI | ❌ | Global only |
| Cline | ❌ | Global only (uses VS Code workspace settings) |

**Re-running `mcpx init`:**
- Loads existing `.mcpx.toml` selection
- Shows current selection pre-checked
- Allows modification
- Updates project configs

---

### 5.3 First Run Behavior

When `mcpx sync` is run and `~/.mcpx/config.toml` doesn't exist:

1. Create `~/.mcpx/` directory
2. Scan all platform configs for existing MCPs
3. Generate `config.toml` with discovered servers
4. Print message:

```
mcpx sync v1.0.0

No config found. Creating ~/.mcpx/config.toml...

Scanning existing platform configurations...
  Found 3 servers in Claude Code
  Found 2 servers in Gemini CLI
  Found 3 servers in Cline

Generated config with 5 unique servers (deduplicated).
Edit ~/.mcpx/config.toml to customize, then run 'mcpx sync' again.
```

---

## 6. Architecture

### 6.1 Package Structure

```
mcpx/
├── pyproject.toml           # uv/pip configuration
├── src/
│   └── mcpx/
│       ├── __init__.py      # Version, exports
│       ├── __main__.py      # Entry point for `python -m mcpx`
│       ├── cli.py           # argparse CLI definition
│       ├── config.py        # Config loading/parsing
│       ├── models.py        # Dataclasses (MCPServer, Config)
│       ├── sync.py          # Main sync orchestration
│       ├── platforms/
│       │   ├── __init__.py
│       │   ├── base.py      # Protocol definition
│       │   ├── claude.py    # Claude Code adapter
│       │   ├── gemini.py    # Gemini CLI adapter
│       │   ├── codex.py     # Codex CLI adapter
│       │   ├── roo.py       # Roo Code adapter
│       │   ├── kilo.py      # Kilo Code adapter
│       │   └── cline.py     # Cline adapter
│       └── utils/
│           ├── __init__.py
│           ├── env.py       # Environment variable expansion
│           ├── backup.py    # Backup management
│           └── validation.py # Command/config validation
└── tests/
    ├── __init__.py
    ├── test_config.py
    ├── test_sync.py
    ├── test_platforms/
    │   ├── test_claude.py
    │   └── ...
    └── fixtures/
        ├── sample_config.toml
        └── platform_configs/
```

### 6.2 Core Types

```python
# src/mcpx/models.py
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

@dataclass(frozen=True)
class MCPServer:
    """Immutable MCP server configuration."""
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)

@dataclass
class Config:
    """mcpx configuration."""
    version: str
    servers: dict[str, MCPServer]

@runtime_checkable
class PlatformAdapter(Protocol):
    """Protocol for platform-specific adapters."""

    @property
    def name(self) -> str:
        """Human-readable platform name."""
        ...

    @property
    def config_path(self) -> Path | None:
        """Path to platform config file, or None if not found."""
        ...

    def load(self) -> dict[str, MCPServer]:
        """Load existing MCP servers from platform config."""
        ...

    def save(self, servers: dict[str, MCPServer]) -> None:
        """Save MCP servers to platform config."""
        ...
```

### 6.3 Key Design Decisions

1. **Protocol-based architecture**: Use Python 3.12 Protocols for type-safe adapter pattern without inheritance overhead.

2. **Immutable data models**: `MCPServer` is frozen dataclass to prevent accidental mutation.

3. **Pure functions for logic**: Sync, merge, validation are pure functions for testability.

4. **No runtime dependencies**: Standard library only for core functionality.

5. **Fail-fast on config errors**: Invalid TOML stops execution immediately with clear error.

6. **Graceful degradation on platform errors**: Skip unavailable platforms, report summary.

---

## 7. Platform Adapters

### 7.1 Output Format Examples

#### Claude Code (`~/.claude.json`)

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/user/projects"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxxx"
      }
    }
  }
}
```

#### Gemini CLI (`~/.gemini/settings.json`)

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/user/projects"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxxx"
      }
    }
  },
  "selectedAuthType": "...",
  "theme": "..."
}
```

Note: Preserves existing non-MCP settings.

#### Codex CLI (`~/.codex/config.toml`)

```toml
[mcp_servers.filesystem]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/Users/user/projects"]

[mcp_servers.github]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { GITHUB_PERSONAL_ACCESS_TOKEN = "ghp_xxxx" }
```

Note: Uses `mcp_servers` (underscore) not `mcpServers`.

#### VS Code Extensions (Roo/Kilo/Cline)

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/user/projects"],
      "disabled": false,
      "alwaysAllow": []
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxxx"
      },
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

Note: Adds platform-required defaults (`disabled`, `alwaysAllow`).

---

## 8. Error Handling

### 8.1 Error Categories

| Category | Behavior | Example |
|----------|----------|---------|
| **Config Parse Error** | Exit immediately | Invalid TOML syntax |
| **Missing Required Field** | Exit immediately | Server without `command` |
| **Command Not Found** | Skip server, continue | `command: nonexistent` |
| **Platform Config Missing** | Skip platform, continue | VS Code not installed |
| **Platform Write Error** | Report error, continue | Permission denied |
| **Env Var Not Set** | Warn, sync anyway | `${MISSING_VAR}` |

### 8.2 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (all platforms synced) |
| 1 | Partial success (some platforms failed) |
| 2 | Config error (invalid TOML, missing fields) |
| 3 | Fatal error (unexpected exception) |

---

## 9. Testing Strategy

### 9.1 Unit Tests

- Config parsing (valid/invalid TOML)
- Environment variable expansion
- Server validation
- Platform format conversions

### 9.2 Integration Tests

- End-to-end sync to temp directories
- Backup creation verification
- Orphan preservation
- Platform config file creation

### 9.3 Test Fixtures

```
tests/fixtures/
├── valid_config.toml
├── invalid_config.toml
├── platform_configs/
│   ├── claude.json
│   ├── gemini.json
│   ├── codex.toml
│   └── cline.json
```

---

## 10. Dependencies

### 10.1 Runtime Dependencies

**None** - Standard library only:

- `tomllib` (Python 3.11+ built-in)
- `json` (built-in)
- `pathlib` (built-in)
- `argparse` (built-in)
- `shutil` (built-in)
- `dataclasses` (built-in)
- `typing` (built-in)

### 10.2 Development Dependencies

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
    "ruff>=0.4",
    "mypy>=1.10",
]
```

### 10.3 Build Dependencies

- `uv` for dependency management
- `build` for package building
- `twine` for PyPI publishing

---

## 11. Project Setup

### 11.1 pyproject.toml

```toml
[project]
name = "mcpx"
version = "0.1.0"
description = "Universal MCP server sync manager for AI coding assistants"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.12"
authors = [{ name = "Your Name", email = "you@example.com" }]
keywords = ["mcp", "ai", "claude", "gemini", "codex", "sync"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Software Development :: Build Tools",
]

dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
    "ruff>=0.4",
    "mypy>=1.10",
]

[project.scripts]
mcpx = "mcpx.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/mcpx"]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]

[tool.mypy]
python_version = "3.12"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --cov=mcpx --cov-report=term-missing"
```

---

## 12. Implementation Phases

### Phase 1: v0.1.0 (MVP)

- [ ] Core config loading/parsing
- [ ] Environment variable expansion
- [ ] Claude Code adapter
- [ ] Gemini CLI adapter
- [ ] Basic sync command
- [ ] List command
- [ ] Unit tests

### Phase 2: v0.2.0

- [ ] Codex CLI adapter (TOML output)
- [ ] Validate command
- [ ] Command existence validation
- [ ] Backup system
- [ ] Integration tests

### Phase 3: v0.3.0

- [ ] Cline adapter
- [ ] Roo Code adapter
- [ ] Kilo Code adapter
- [ ] Auto-detect first run
- [ ] Comprehensive error messages

### Phase 4: v1.0.0

- [ ] Documentation
- [ ] PyPI publishing
- [ ] CI/CD setup
- [ ] Full test coverage

---

## 13. Open Questions (Resolved)

| Question | Resolution |
|----------|------------|
| How to handle HTTP/SSE servers? | Excluded from v1.0 - focus on stdio only |
| Support Windows? | Yes, all paths defined for Windows |
| Handle VS Code Insiders? | Yes, check both Code and Code - Insiders paths |
| Project-level configs? | No, v1.0 is global only |
| Remote sync? | No, local filesystem only |

---

## 14. Success Criteria

1. **Single command sync**: `mcpx sync` updates all 6 platforms
2. **Zero runtime dependencies**: Installs with just `pip install mcpx`
3. **Clear error messages**: Users can fix issues without reading source
4. **Backup safety**: Never lose existing config data
5. **Sub-second performance**: Sync completes in < 1 second

---

## Appendix A: Research Sources

- [OpenAI Codex MCP Documentation](https://developers.openai.com/codex/mcp/)
- [OpenAI Codex Config Reference](https://developers.openai.com/codex/config-reference/)
- [Gemini CLI MCP Documentation](https://geminicli.com/docs/tools/mcp-server/)
- [Roo Code MCP Documentation](https://docs.roocode.com/features/mcp/using-mcp-in-roo)
- [Kilo Code MCP Documentation](https://kilo.ai/docs/features/mcp/using-mcp-in-kilo-code)
- [Cline MCP Configuration](https://docs.cline.bot/mcp/configuring-mcp-servers)
- [Claude Code Settings](https://code.claude.com/docs/en/settings)

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **MCP** | Model Context Protocol - standard for AI tool integrations |
| **Source of truth** | Single authoritative config that all platforms sync from |
| **Orphan** | MCP server in platform config not defined in mcpx config |
| **Adapter** | Platform-specific code for reading/writing configs |
| **stdio** | Standard input/output - local process communication |
| **SSE** | Server-Sent Events - HTTP-based communication (not supported v1.0) |

---

## Appendix C: Detailed Implementation Plan

### C.1 Overview

This plan covers the complete implementation of `mcpx` from project cleanup to final release. The implementation replaces the existing monolithic code with a clean, modular architecture.

### C.2 Phase 0: Project Cleanup and Setup

**Goal:** Clear old code and establish the new project structure.

**Complexity:** Simple

#### Files to Remove

| File | Reason |
|------|--------|
| `mcp-sync-manager.py` | Old monolithic implementation |
| `mcp-sync-manager-v1.py` | Old version (untracked) |
| `mcp-sync` | Old shell script |
| `requirements.txt` | Replaced by pyproject.toml |
| `test_mcp_sync_manager.py` | Old test file |
| `verify_paths.py` | Verification script no longer needed |
| `__pycache__/` | Cached bytecode |
| `VERIFICATION_REPORT.md` | Old report |
| `QUICKSTART.md` | Will be replaced with new docs |

#### Files to Keep

| File | Reason |
|------|--------|
| `README.md` | Update with new content |
| `.claude/spec/mcpx-specification.md` | This specification |
| `.git/` | Version control |

#### New Directory Structure

```
mcpx/
├── pyproject.toml
├── README.md
├── .gitignore
├── src/
│   └── mcpx/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── config.py
│       ├── models.py
│       ├── sync.py
│       ├── platforms/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── claude.py
│       │   ├── gemini.py
│       │   ├── codex.py
│       │   ├── roo.py
│       │   ├── kilo.py
│       │   └── cline.py
│       └── utils/
│           ├── __init__.py
│           ├── env.py
│           ├── backup.py
│           └── validation.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_config.py
    ├── test_models.py
    ├── test_sync.py
    ├── test_env.py
    ├── test_validation.py
    ├── test_platforms/
    │   └── ...
    └── fixtures/
        └── ...
```

#### Implementation Steps

1. Remove old files: `git rm` tracked files, `rm -rf` untracked
2. Create directory structure: `mkdir -p src/mcpx/{platforms,utils} tests/{test_platforms,fixtures}`
3. Create `pyproject.toml` from spec section 11.1
4. Create `.gitignore` for Python
5. Initialize uv: `uv sync`
6. Verify: `uv run python -c "import mcpx"`

#### Testing Checkpoint

- [ ] `uv sync` completes without errors
- [ ] `uv run pytest` runs (even if no tests)
- [ ] Directory structure matches specification

---

### C.3 Phase 1: Core Data Models and Config Loading

**Goal:** Implement foundational data structures and config parsing.

**Complexity:** Medium

**Dependencies:** Phase 0 complete

#### Files to Create

| File | Purpose | Complexity |
|------|---------|------------|
| `src/mcpx/__init__.py` | Package init, version export | Simple |
| `src/mcpx/models.py` | MCPServer, Config, PlatformAdapter Protocol | Medium |
| `src/mcpx/config.py` | TOML loading, config path management | Medium |
| `src/mcpx/utils/env.py` | `${VAR}` expansion | Simple |
| `src/mcpx/utils/__init__.py` | Utils exports | Simple |

#### Key Implementation Notes

**models.py:**
- Use `@dataclass(frozen=True)` for immutability
- Use `tuple[str, ...]` for args (immutable)
- Protocol with `@runtime_checkable` for adapters

**config.py:**
- Use built-in `tomllib` (Python 3.11+)
- `get_config_path()` returns `~/.mcpx/config.toml`
- `ensure_config_dir()` creates directory if missing
- Fail-fast on TOML parse errors

**utils/env.py:**
- Regex: `\$\{([A-Z_][A-Z0-9_]*)\}`
- Return original if not found (warn, don't fail)

#### Tests to Create

| File | Tests |
|------|-------|
| `tests/test_models.py` | Creation, immutability, equality |
| `tests/test_config.py` | Valid/invalid TOML, missing fields |
| `tests/test_env.py` | Expansion, missing vars |

#### Fixtures to Create

- `tests/fixtures/valid_config.toml`
- `tests/fixtures/invalid_config.toml`
- `tests/fixtures/minimal_config.toml`

---

### C.4 Phase 2: JSON Platform Adapters (Claude, Gemini)

**Goal:** Implement adapters for JSON-based platforms.

**Complexity:** Medium

**Dependencies:** Phase 1 complete

#### Files to Create

| File | Purpose | Complexity |
|------|---------|------------|
| `src/mcpx/platforms/base.py` | Protocol, JSON helpers | Medium |
| `src/mcpx/platforms/claude.py` | Claude Code adapter | Simple |
| `src/mcpx/platforms/gemini.py` | Gemini CLI adapter | Simple |
| `src/mcpx/platforms/__init__.py` | Platform registry | Simple |

#### Key Implementation Notes

**base.py:**
- Define `PlatformAdapter` Protocol
- JSON read/write helpers with error handling
- Backup integration

**claude.py:**
- Path: `~/.claude.json`
- Key: `mcpServers`
- Create file if missing

**gemini.py:**
- Path: `~/.gemini/settings.json`
- Key: `mcpServers`
- Preserve other settings (`selectedAuthType`, `theme`, etc.)

#### Tests to Create

- `tests/test_platforms/test_claude.py`
- `tests/test_platforms/test_gemini.py`

---

### C.5 Phase 3: Validation and Backup Utilities

**Goal:** Implement command validation and backup system.

**Complexity:** Medium

**Dependencies:** Phase 1 complete (parallel to Phase 2)

#### Files to Create

| File | Purpose | Complexity |
|------|---------|------------|
| `src/mcpx/utils/validation.py` | Command/config validation | Medium |
| `src/mcpx/utils/backup.py` | Timestamped backups | Simple |

#### Key Implementation Notes

**validation.py:**
- Use `shutil.which()` for command lookup
- Return `ValidationError` objects with severity
- Check required fields, warn on missing env vars

**backup.py:**
- Format: `{platform}_{YYYYMMDD}_{HHMMSS}.{ext}`
- Location: `~/.mcpx/backups/`
- Use `shutil.copy2()` for metadata preservation

---

### C.6 Phase 4: Sync Orchestration and Basic CLI

**Goal:** Implement core sync logic and CLI commands.

**Complexity:** Complex

**Dependencies:** Phases 1, 2, 3 complete

#### Files to Create

| File | Purpose | Complexity |
|------|---------|------------|
| `src/mcpx/sync.py` | Sync orchestration | Complex |
| `src/mcpx/cli.py` | argparse CLI | Medium |
| `src/mcpx/__main__.py` | Module entry point | Simple |

#### Key Implementation Notes

**sync.py:**
```python
def sync_all(config: Config) -> SyncReport:
    """
    1. Validate config
    2. Expand env vars
    3. For each platform:
       a. Create backup
       b. Load existing
       c. Merge (preserve orphans)
       d. Save
    4. Return report
    """
```

**cli.py:**
- Commands: `sync`, `list`, `validate`
- Exit codes: 0 (success), 1 (partial), 2 (config error), 3 (fatal)
- Verbose output by default

---

### C.7 Phase 5: Codex CLI Adapter (TOML Output)

**Goal:** Add TOML output support for Codex CLI.

**Complexity:** Medium

**Dependencies:** Phase 4 complete

#### Files to Create/Update

| File | Purpose | Complexity |
|------|---------|------------|
| `src/mcpx/platforms/codex.py` | Codex adapter | Medium |
| `src/mcpx/utils/toml_writer.py` | Minimal TOML writer | Medium |

#### Key Challenge

Python's `tomllib` is read-only. Must implement minimal TOML writer:

```python
def write_toml_simple(data: dict, path: Path) -> None:
    """Write simple TOML (command, args, env only)."""
```

#### Field Name Translation

- Input (mcpx): `servers`
- Output (Codex): `mcp_servers` (snake_case)

---

### C.8 Phase 6: VS Code Extension Adapters

**Goal:** Add Cline, Roo Code, Kilo Code adapters.

**Complexity:** Medium

**Dependencies:** Phase 4 complete (parallel to Phase 5)

#### Files to Create

| File | Path Pattern |
|------|--------------|
| `src/mcpx/platforms/cline.py` | `saoudrizwan.claude-dev` |
| `src/mcpx/platforms/roo.py` | `rooveterinaryinc.roo-cline` |
| `src/mcpx/platforms/kilo.py` | `kilocode.kilocode` |

#### Key Implementation Notes

- OS-specific paths (macOS, Linux, Windows)
- Check both VS Code and VS Code Insiders
- Add required defaults: `disabled: false`, `alwaysAllow: []`
- Different filename for Kilo (`mcp_settings.json` not `cline_mcp_settings.json`)

#### Consider Shared Base

```python
class VSCodeExtensionAdapter:
    def __init__(self, extension_id: str, settings_filename: str):
        ...
```

---

### C.9 Phase 7: Validate Command, First-Run, and Project Init

**Goal:** Complete `validate` command, auto-detect, and `mcpx init` for project-level configs.

**Complexity:** Medium-Complex

**Dependencies:** Phases 5, 6 complete

#### Enhancements

**validate command:**
- TOML syntax check
- Required fields check
- Command existence check
- Env var warnings

**First-run auto-detect:**
```python
def first_run_init() -> SyncReport:
    """
    1. Create ~/.mcpx/
    2. Scan all platforms
    3. Deduplicate servers
    4. Generate config.toml
    5. Print instructions
    """
```

**mcpx init command (NEW):**
```python
def cmd_init() -> int:
    """
    Interactive project-level MCP selection.

    1. Load global config
    2. Load existing .mcpx.toml if present (pre-select)
    3. Present interactive multi-select UI
    4. Write .mcpx.toml with selected servers
    5. Sync to platforms with project-level support:
       - Claude Code: .mcp.json
       - Roo Code: .roo/mcp.json
       - Kilo Code: .kilocode/mcp.json
    """
```

#### Files to Create/Update

| File | Purpose | Complexity |
|------|---------|------------|
| `src/mcpx/cli.py` | Add `init` subcommand | Simple |
| `src/mcpx/init.py` | Interactive selection logic | Medium |
| `src/mcpx/platforms/claude.py` | Add project-level `.mcp.json` support | Simple |
| `src/mcpx/platforms/roo.py` | Add project-level `.roo/mcp.json` support | Simple |
| `src/mcpx/platforms/kilo.py` | Add project-level `.kilocode/mcp.json` support | Simple |

#### Interactive Selection UI

For zero-dependency interactive selection, use:
- `sys.stdin` for input
- ANSI escape codes for cursor movement
- Simple arrow key + space + enter interaction

```python
def interactive_select(items: list[str], preselected: set[str]) -> list[str]:
    """
    Terminal-based multi-select without external dependencies.
    Returns list of selected item names.
    """
```

#### Project Config Schema

```toml
# .mcpx.toml (in project root)
[mcpx]
version = "1.0"
servers = ["filesystem", "github", "context7"]
```

#### Platform Project Paths

| Platform | Adapter Method | Project Config Path |
|----------|----------------|---------------------|
| Claude Code | `save_project()` | `.mcp.json` |
| Roo Code | `save_project()` | `.roo/mcp.json` |
| Kilo Code | `save_project()` | `.kilocode/mcp.json` |

---

### C.10 Phase 8: Documentation and Polish

**Goal:** Complete docs, error messages, final polish.

**Complexity:** Simple

**Dependencies:** Phases 1-7 complete

#### Files to Update

- `README.md` - Full documentation
- `.gitignore` - Python gitignore
- All error messages - Make actionable

#### Final Checklist

- [ ] `uv run pytest` - All tests pass
- [ ] `uv run mypy src/mcpx --strict` - Type check passes
- [ ] `uv run ruff check src tests` - Lint passes
- [ ] README is complete and accurate

---

### C.11 Dependency Graph

```
Phase 0 (Setup)
    │
    ▼
Phase 1 (Models + Config)
    │
    ├────────────────────┐
    ▼                    ▼
Phase 2 (Claude/Gemini)  Phase 3 (Validation/Backup)
    │                    │
    └────────┬───────────┘
             ▼
    Phase 4 (Sync + CLI)
             │
    ┌────────┴────────┐
    ▼                 ▼
Phase 5 (Codex)   Phase 6 (VS Code)
    │                 │
    └────────┬────────┘
             ▼
    Phase 7 (Validate + Auto-detect)
             │
             ▼
    Phase 8 (Docs + Polish)
```

---

### C.12 Risk Areas

#### Critical Risks

1. **TOML Writing Without Dependencies**
   - Python's `tomllib` is read-only
   - Must implement minimal writer for Codex
   - Mitigation: Test extensively, handle only our subset

2. **VS Code Path Detection**
   - Paths vary by OS and VS Code variant
   - Mitigation: Check multiple paths, graceful fallback

3. **Config Format Compatibility**
   - Platforms may change formats
   - Mitigation: Defensive parsing, preserve unknown fields

#### Medium Risks

4. **Environment Variable Expansion**
   - Expand at sync time per spec
   - Mitigation: Clear documentation of behavior

5. **Orphan Preservation**
   - Must not delete platform-native MCPs
   - Mitigation: Merge logic preserves unknown keys

---

### C.13 Critical Files Summary

| File | Why Critical |
|------|--------------|
| `src/mcpx/models.py` | Core data structures everything depends on |
| `src/mcpx/config.py` | Config loading is foundation for all operations |
| `src/mcpx/sync.py` | Main orchestration, merge logic, first-run |
| `src/mcpx/platforms/base.py` | Adapter protocol all platforms implement |
| `pyproject.toml` | Enables build and distribution |
