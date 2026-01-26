# Technology Stack

**Analysis Date:** 2026-01-26

## Languages

**Primary:**
- Python 3.12+ - Main implementation language, required by `pyproject.toml` (requires-python = ">=3.12")

**Secondary:**
- Python 3.13, 3.14 - Supported versions per classifiers in `pyproject.toml`

## Runtime

**Environment:**
- Python 3.12 or later (mandatory)
- Works on macOS, Linux, and Windows (cross-platform PATH handling via `shutil`)

**Package Manager:**
- uv - Build and dependency management (modern Python build system)
  - Lockfile: `uv.lock` present - frozen dependencies with exact versions
  - Project config: `pyproject.toml` using `hatchling` build backend

## Frameworks

**Core:**
- No web framework - Pure CLI application built with `argparse`
- Structured as Python package in `src/mcpx/` following standard Python layout

**Command Line:**
- `argparse` (stdlib) - CLI argument parsing and subcommand handling
- Entry point: `src/mcpx/cli.py:main()` exposed as `mcpx` command via `pyproject.toml` scripts

**Testing:**
- pytest 8.0+ - Test runner
- pytest-cov 4.0+ - Code coverage reporting
- Test discovery: `tests/` directory

**Development:**
- ruff 0.4+ - Linting (E, F, I, N, W, UP, B, C4, SIM rules enabled)
- mypy 1.10+ - Type checking with strict mode enabled
- Coverage requirement integrated with pytest

## Key Dependencies

**Critical:**
- tomli 2.0.0+ - TOML parsing for Codex CLI platform (TOML format support)

**Standard Library Only (Minimal External Deps):**
- `json` (stdlib) - JSON parsing for config files and all platform configs
- `subprocess` (stdlib) - Process spawning for stdio MCP server health checks
- `urllib` (stdlib) - HTTP requests for HTTP MCP server health checks (urllib.request, urllib.error)
- `shutil` (stdlib) - Command PATH lookup, file copying for backups
- `pathlib` (stdlib) - Cross-platform file path handling
- `dataclasses` (stdlib) - Data models for Config, MCPServer, validation results
- `typing` (stdlib) - Type hints and Protocol definitions
- `re` (stdlib) - Regex for environment variable expansion and validation
- `os` (stdlib) - Environment variable access
- `warnings` (stdlib) - User warnings for unset env vars
- `logging` (stdlib) - Optional logging infrastructure
- `datetime` (stdlib) - Timestamp generation for backups
- `argparse` (stdlib) - CLI argument parsing

**Notably Minimal:**
- No external HTTP library (uses stdlib urllib instead)
- No ORM or database library (filesystem-based JSON configs only)
- No async framework (synchronous blocking I/O)
- No dependency injection framework
- No external validation library

## Configuration

**Environment:**
- Custom configuration at `~/.mcpx/config.json` (user home directory)
- Project-level configs: `.mcp.json`, `.roo/mcp.json`, `.kilocode/mcp.json`
- Platform configs auto-detected from user home (Claude, Gemini, Codex, Cline, Roo, Kilo)
- Environment variable expansion in config: `${VAR_NAME}` syntax expanded at runtime

**Build:**
- `pyproject.toml` - Single source of truth for package metadata, dependencies, build, and tool config
- Build backend: `hatchling` (minimal, pure Python build system)
- Wheel package: packages `src/mcpx` tree into wheel

## Platform Requirements

**Development:**
- Python 3.12+ installed
- uv package manager (for development workflow)
- git (for version control)
- System tools: npm/npx (for testing MCP servers), standard POSIX tools

**Production:**
- Python 3.12+ runtime
- No external services required
- Read/write access to user home directory for config files
- Network access optional (only needed for HTTP MCP server health checks)
- Platform-specific config file access (Claude Code, Gemini CLI, Codex CLI, etc.)

## Deployment

**Package Distribution:**
- Distributes as wheel and sdist via Python packaging ecosystem
- Installed via `pip install mcpx` or `uv pip install mcpx`
- Installed from source via `uv pip install -e .` for development

**Installation Target:**
- Global Python environment or virtual environment
- Executable installed to Python bin directory as `mcpx` command

---

*Stack analysis: 2026-01-26*
