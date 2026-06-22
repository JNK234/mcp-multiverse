# mcpx Research Memo: AI Coding Tool Config Formats & Best Practices

**Date:** 2026-01-26
**Issue:** #9 - Research backlog: tools, config formats, patterns, and best practices

---

## Executive Summary

This document captures research findings on MCP server configuration formats, capabilities, and best practices across 8 AI coding assistants. The research informs mcpx's evolution into a Universal AI Toolchain Manager.

---

## 1. Tool Capability Matrix

| Tool | Format | Global Config | Project Config | MCP | Skills/Modes | Commands | Models | Auth |
|------|--------|---------------|----------------|-----|--------------|----------|--------|------|
| **Claude Code** | JSON | `~/.claude.json` | `.mcp.json` | ✅ | ✅ | ✅ | ✅ | API Key |
| **Gemini CLI** | JSON | `~/.gemini/settings.json` | ❌ | ✅ | ❌ | ❌ | ✅ | OAuth |
| **Codex CLI** | TOML | `~/.codex/config.toml` | ❌ (requested) | ✅ | ✅ | ❌ | ✅ | API Key |
| **Cline** | JSON | VS Code globalStorage | ❌ | ✅ | ❌ | ❌ | ✅ | API Key |
| **Roo Code** | JSON/YAML | VS Code globalStorage | `.roo/mcp.json` | ✅ | ✅ (modes) | ❌ | ✅ | API Key |
| **Kilo Code** | JSON | VS Code globalStorage | `.kilocode/mcp.json` | ✅ | ✅ (modes) | ❌ | ✅ | API Key |
| **OpenCode** | TOML | `~/.config/opencode/config.toml` | `.opencode/config.toml` | ✅ | ❌ | ❌ | ✅ | API Key |

---

## 2. Detailed Tool Configuration

### 2.1 Claude Code (Anthropic)

**Config Locations:**
- Global: `~/.claude.json`
- Project: `.mcp.json` in project root
- Settings: `~/.claude/settings.json`

**MCP Server Schema:**
```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

**HTTP Server Schema:**
```json
{
  "mcpServers": {
    "remote-server": {
      "type": "url",
      "url": "https://mcp.example.com/api",
      "headers": {
        "Authorization": "Bearer ${TOKEN}"
      }
    }
  }
}
```

**Supported Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `command` | string | Yes (stdio) | Executable to run |
| `args` | array | No | Command arguments |
| `env` | object | No | Environment variables |
| `type` | string | No | `"url"` for HTTP servers |
| `url` | string | Yes (http) | Server endpoint URL |
| `headers` | object | No | HTTP headers |

**Skills/Custom Instructions:**
- Location: `~/.claude/commands/` directory
- Format: Markdown files with YAML frontmatter
- Project-level: `.claude/commands/` in project

**Capabilities:**
- ✅ Global MCP config
- ✅ Project-level MCP config
- ✅ Skills (custom commands)
- ✅ Custom instructions (CLAUDE.md)
- ✅ Model preferences
- ❌ Multi-account support
- ❌ Profile switching

**Sources:**
- https://docs.anthropic.com/en/docs/claude-code
- https://github.com/anthropics/claude-code

---

### 2.2 Gemini CLI (Google)

**Config Location:**
- Global: `~/.gemini/settings.json`
- No project-level support

**MCP Server Schema:**
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "token"
      }
    }
  },
  "selectedAuthType": "oauth",
  "theme": "dark"
}
```

**Supported Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `command` | string | Yes | Executable to run |
| `args` | array | No | Command arguments |
| `env` | object | No | Environment variables |

**Other Settings:**
- `selectedAuthType`: Authentication method
- `theme`: UI theme
- Model preferences via CLI flags

**Limitations:**
- No project-level MCP config
- Limited to stdio servers
- No HTTP/SSE server support documented

**Sources:**
- https://github.com/google-gemini/gemini-cli
- https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md

---

### 2.3 Codex CLI (OpenAI)

**Config Location:**
- Global: `~/.codex/config.toml`
- Project: Not officially supported (feature request #2554)

**MCP Server Schema (TOML):**
```toml
[mcp_servers.context7]
enabled = true
command = "npx"
args = ["-y", "@upstash/context7-mcp"]
env = { "API_KEY" = "value" }
env_vars = ["ANOTHER_SECRET"]
cwd = "/path/to/server"
startup_timeout_sec = 10.0
tool_timeout_sec = 60.0
enabled_tools = ["search", "summarize"]
disabled_tools = ["slow-tool"]

[mcp_servers.github]
enabled = true
url = "https://github-mcp.example.com/mcp"
bearer_token_env_var = "GITHUB_TOKEN"
http_headers = { "X-Example" = "value" }
env_http_headers = { "X-Auth" = "AUTH_ENV" }
```

**Supported Fields (STDIO):**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `command` | string | Yes | Executable to run |
| `args` | array | No | Command arguments |
| `env` | object | No | Static env vars |
| `env_vars` | array | No | Whitelist env vars from parent |
| `cwd` | string | No | Working directory |
| `enabled` | boolean | No | Enable/disable server |
| `enabled_tools` | array | No | Allow-list of tools |
| `disabled_tools` | array | No | Deny-list of tools |
| `startup_timeout_sec` | number | No | Startup timeout (default 10s) |
| `tool_timeout_sec` | number | No | Tool timeout (default 60s) |

**Supported Fields (HTTP):**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | Yes | Server endpoint URL |
| `bearer_token_env_var` | string | No | Env var for bearer token |
| `http_headers` | object | No | Static headers |
| `env_http_headers` | object | No | Headers from env vars |

**Other Settings:**
```toml
model = "gpt-5.2-codex"
model_provider = "openai"
model_reasoning_effort = "medium"
approval_policy = "on-request"
sandbox_mode = "read-only"

[profiles.deep-review]
model = "gpt-5-pro"
model_reasoning_effort = "high"

[features]
shell_tool = true
rmcp_client = true  # Required for OAuth MCP
skills = true
```

**Capabilities:**
- ✅ Global MCP config
- ❌ Project-level MCP config (requested)
- ✅ Profiles for different settings
- ✅ Tool filtering (enabled/disabled)
- ✅ OAuth support (with feature flag)
- ✅ Custom model providers

**Sources:**
- https://developers.openai.com/codex/mcp/
- https://developers.openai.com/codex/config-reference/
- https://github.com/openai/codex

---

### 2.4 Cline (VS Code Extension)

**Config Location:**
- Global: `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- Windows: `%APPDATA%/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- Linux: `~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- No project-level MCP config (rules via `.clinerules`)

**MCP Server Schema:**
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-filesystem", "/path"],
      "env": {},
      "alwaysAllow": ["list_directory", "read_file"],
      "disabled": false
    },
    "remote-server": {
      "url": "https://mcp.example.com",
      "type": "streamableHttp",
      "headers": {
        "Authorization": "Bearer token"
      },
      "autoApprove": ["tool1"],
      "timeout": 60,
      "disabled": false
    }
  }
}
```

**Supported Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `command` | string | Yes (stdio) | Executable to run |
| `args` | array | No | Command arguments |
| `env` | object | No | Environment variables |
| `url` | string | Yes (http) | Server endpoint URL |
| `type` | string | No | `"streamableHttp"` or `"sse"` |
| `headers` | object | No | HTTP headers |
| `alwaysAllow` | array | No | Auto-approved tools |
| `autoApprove` | array | No | Alternative to alwaysAllow |
| `disabled` | boolean | No | Disable server |
| `timeout` | number | No | Request timeout (30-3600s) |

**Project Rules (not MCP config):**
- `.clinerules` file in project root
- `.clinerules/` directory for multiple rule files
- `AGENTS.md` as fallback

**Sources:**
- https://docs.cline.bot/mcp/configuring-mcp-servers
- https://docs.cline.bot/features/cline-rules

---

### 2.5 Roo Code (VS Code Extension)

**Config Location:**
- Global: `~/Library/Application Support/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json`
- Project: `.roo/mcp.json`
- Custom Modes: `settings/custom_modes.yaml` or `custom_modes.json`
- Project Modes: `.roomodes` (YAML or JSON)

**MCP Server Schema:**
```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "server-package"],
      "env": {},
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

**Custom Modes Schema (YAML):**
```yaml
customModes:
  - slug: docs-writer
    name: 📝 Documentation Writer
    description: A mode for writing technical documentation
    roleDefinition: You are a technical writer...
    whenToUse: Use for documentation tasks
    customInstructions: |
      Follow style guide
      Use clear language
    groups:
      - read
      - - edit
        - fileRegex: \\.md$
          description: Markdown files only
      - command
```

**Mode Groups:**
- `read`: Read files
- `edit`: Edit files (with optional fileRegex)
- `browser`: Browser tools
- `command`: Terminal commands
- `mcp`: MCP tools

**Project Rules:**
- `.roo/rules-{mode-slug}/` directory
- `.roorules-{mode-slug}` file (fallback)
- `.roo/rules/` for shared rules

**Sources:**
- https://docs.roocode.com/features/mcp/using-mcp-in-roo
- https://docs.roocode.com/features/custom-modes

---

### 2.6 Kilo Code (VS Code Extension)

**Config Location:**
- Global: `~/Library/Application Support/Code/User/globalStorage/kilocode.kilo-code/settings/mcp_settings.json`
- Project: `.kilocode/mcp.json`
- CLI: `~/.config/kilo/mcp.json`

**MCP Server Schema:**
```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "server-package"],
      "env": {},
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

**Limitations:**
- Server names must be > 3 characters (bug #4578)
- Similar to Cline/Roo format

**Sources:**
- https://kilo.ai/docs/features/mcp/using-mcp-in-kilo-code
- https://kilo.ai/docs/features/mcp/using-mcp-in-cli

---

### 2.7 OpenCode (SST)

**Config Location:**
- Global: `~/.config/opencode/config.toml`
- Project: `.opencode/config.toml`

**MCP Server Schema (TOML):**
```toml
[mcp.server-name]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { "GITHUB_TOKEN" = "token" }
```

**Other Settings:**
```toml
[provider.anthropic]
api_key = "${ANTHROPIC_API_KEY}"
model = "claude-3-opus"

[provider.openai]
api_key = "${OPENAI_API_KEY}"
model = "gpt-4"
```

**Sources:**
- https://github.com/sst/opencode
- https://opencode.ai/docs

---

## 3. MCP Protocol Overview

### 3.1 Transport Types

| Transport | Use Case | Configuration |
|-----------|----------|---------------|
| **STDIO** | Local servers | `command` + `args` |
| **HTTP** | Remote servers | `url` + optional auth |
| **SSE** | Legacy remote | `url` + `type: "sse"` |
| **Streamable HTTP** | Modern remote | `url` + `type: "streamableHttp"` |

### 3.2 Standard Fields Across Implementations

**Common Fields (all tools):**
- `command` (string): Executable for stdio servers
- `args` (array): Command arguments
- `env` (object): Environment variables

**Common Optional Fields:**
- `disabled`/`enabled` (boolean): Enable/disable server
- `url` (string): HTTP server endpoint
- `headers` (object): HTTP headers

**Tool-Specific Fields:**
- `alwaysAllow`/`autoApprove` (Cline, Roo, Kilo): Auto-approved tools
- `enabled_tools`/`disabled_tools` (Codex): Tool filtering
- `timeout` (various): Request timeout
- `cwd` (Codex): Working directory

### 3.3 Environment Variable Patterns

**Syntax Variations:**
| Tool | Syntax | Example |
|------|--------|---------|
| All | `${VAR}` | `"${GITHUB_TOKEN}"` |
| Bash | `${VAR:-default}` | `"${API_KEY:-fallback}"` |
| Codex | `env_vars` array | `env_vars = ["SECRET"]` |

**Best Practices:**
1. Use `${VAR}` syntax for portability
2. Support `${VAR:-default}` for defaults
3. Validate references exist before sync
4. Never expand secrets into platform configs (security risk)
5. Use secret providers (1Password, Keychain) for production

---

## 4. Secret Management Patterns

### 4.1 Provider Integration

**1Password CLI:**
```bash
# Reference format
op://vault/item/field

# Inject at runtime
op inject -i config.template -o config.json
op run --env-file=.env -- command
```

**macOS Keychain:**
```bash
# Store
security add-generic-password -a "account" -s "service" -w "password"

# Retrieve
security find-generic-password -a "account" -s "service" -w
```

**HashiCorp Vault:**
```bash
vault kv get secret/myapp/config
```

### 4.2 Redaction Strategies

1. **Pattern-based**: Use regex to detect and redact secrets in logs
2. **Structured logging**: Tag sensitive fields for automatic redaction
3. **HMAC hashing**: Replace values with deterministic hashes
4. **Terraform pattern**: Mark variables as `sensitive = true`

### 4.3 Multi-Account Patterns

**direnv:**
```bash
# ~/work/.envrc
export GIT_CONFIG_GLOBAL=$(pwd)/.gitconfig
export AWS_PROFILE=work

# ~/personal/.envrc
export GIT_CONFIG_GLOBAL=$(pwd)/.gitconfig
export AWS_PROFILE=personal
```

**Git Conditional Includes:**
```gitconfig
[includeIf "gitdir:~/work/"]
    path = ~/.gitconfig-work
[includeIf "gitdir:~/personal/"]
    path = ~/.gitconfig-personal
```

---

## 5. Conflict Resolution Strategies

### 5.1 Timestamp-Based (Newest Wins)

**Pros:**
- Simple to implement
- Predictable behavior
- No user intervention needed

**Cons:**
- May lose intentional changes
- Clock skew issues

**Implementation:**
```python
def resolve_conflict(master_server, platform_server):
    if platform_server.last_modified > master_server.last_modified:
        return platform_server
    return master_server
```

### 5.2 Source Priority

**Pros:**
- Explicit control
- Deterministic

**Pattern:**
```
Priority: project > user > global > default
```

### 5.3 Manual Resolution

**Pattern:**
```json
{
  "conflicts": [
    {
      "server": "github",
      "sources": ["claude", "codex"],
      "differences": ["env.GITHUB_TOKEN"],
      "resolution": "pending"
    }
  ]
}
```

---

## 6. Recommendations for mcpx

### 6.1 Schema v2 Design

**Unified Server Schema:**
```json
{
  "servers": {
    "server-name": {
      "type": "stdio | http | sse",
      "command": "npx",
      "args": ["-y", "package"],
      "url": "https://...",
      "env": {},
      "headers": {},
      "auth": {
        "type": "bearer | oauth | api_key",
        "token_env": "TOKEN_VAR"
      },
      "options": {
        "timeout": 60,
        "enabled_tools": [],
        "disabled_tools": []
      },
      "metadata": {
        "last_modified": "2026-01-26T00:00:00Z",
        "source": "claude",
        "provenance": "imported"
      }
    }
  }
}
```

### 6.2 Profile System

```json
{
  "profiles": {
    "work": {
      "servers": ["github-work", "jira", "confluence"],
      "env_file": "~/.env.work"
    },
    "personal": {
      "servers": ["github-personal", "notion"],
      "env_file": "~/.env.personal"
    }
  },
  "active_profile": "work"
}
```

### 6.3 Adapter Capabilities

| Capability | Claude | Gemini | Codex | Cline | Roo | Kilo | OpenCode |
|------------|--------|--------|-------|-------|-----|------|----------|
| Read MCP | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Write MCP | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Read Skills | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ |
| Write Skills | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| Project Config | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| HTTP Servers | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Tool Filtering | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Preserve Fields | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

### 6.4 Priority Implementation Order

1. **Phase A: Fix current gaps** (Issue #1)
   - Integrate health checks
   - Fix backup naming
   - Preserve platform fields

2. **Phase B: Bidirectional sync** (Issue #3)
   - Add metadata tracking
   - Implement merge with timestamps
   - Add dry-run mode

3. **Phase C: Adapter framework v2** (Issue #4)
   - Capability matrix per adapter
   - Normalized intermediate representation

4. **Phase D: Profile management** (Issue #5)
   - Multi-account support
   - Profile switching

5. **Phase E: Security** (Issue #6)
   - Secret provider integration
   - Redaction middleware

---

## 7. Sources Index

### Official Documentation
- Claude Code: https://docs.anthropic.com/en/docs/claude-code
- Gemini CLI: https://github.com/google-gemini/gemini-cli
- Codex CLI: https://developers.openai.com/codex/
- Cline: https://docs.cline.bot/
- Roo Code: https://docs.roocode.com/
- Kilo Code: https://kilo.ai/docs/
- OpenCode: https://opencode.ai/docs

### MCP Protocol
- Specification: https://modelcontextprotocol.io/specification/
- GitHub: https://github.com/modelcontextprotocol

### Secret Management
- 1Password CLI: https://developer.1password.com/docs/cli/
- HashiCorp Vault: https://developer.hashicorp.com/vault/docs/
- OWASP Secrets Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html

---

*Research conducted: 2026-01-26*
*Last updated: 2026-01-26*
