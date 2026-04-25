# MCP Server Management

This guide covers the `dva mcp` commands for managing Model Context Protocol (MCP) servers across your development environment.

## Overview

The MCP management system provides:
- **Centralized configuration** - Single source of truth for all MCP servers
- **IDE sync** - Generate IDE-specific configs (Windsurf, Claude, VS Code, Cursor)
- **Docker support** - Manage Docker-based MCP servers
- **Health monitoring** - Check server availability and status
- **Project-level configs** - Override global settings per workspace

## Quick Start

```bash
# Initialize MCP in your workspace
dva mcp init

# Add your existing servers
dva mcp add kg --type docker --compose ./kg-mcp-infrastructure/docker-compose.yml --port 8125
dva mcp add glean --type stdio --command python --args "/path/to/glean_server.py"

# List configured servers
dva mcp list

# Start Docker servers
dva mcp start

# Check health
dva mcp health

# Sync to your IDE
dva mcp sync --ide windsurf
```

## Configuration

### Global Registry

Global MCP servers are stored in `~/.dva-agentic/mcp/registry.json`:

```json
{
  "version": "1.0",
  "servers": {
    "kg": {
      "name": "DVA Knowledge Graph",
      "type": "docker",
      "enabled": true,
      "docker": {
        "compose_file": "/path/to/docker-compose.yml",
        "service": "kg-mcp-server",
        "port": 8125
      },
      "url": "http://localhost:8125",
      "transport": "http",
      "tools": ["kg_query", "kg_search", "kg_stats"]
    },
    "glean": {
      "name": "Glean Search",
      "type": "stdio",
      "enabled": true,
      "command": "python",
      "args": ["/path/to/glean_server.py"],
      "env": {
        "GLEAN_API_TOKEN": "${GLEAN_API_TOKEN}"
      }
    }
  }
}
```

### Project Configuration

Project-specific settings in `.mcp/mcp.json`:

```json
{
  "version": "1.0",
  "inherit_global": true,
  "servers": {
    "kg": { "enabled": true },
    "glean": { "enabled": false },
    "project-tool": {
      "name": "Project Tool",
      "type": "stdio",
      "command": "python",
      "args": ["./tools/my_tool.py"],
      "enabled": true
    }
  }
}
```

## Commands

### `dva mcp init`

Initialize MCP configuration in the current workspace.

```bash
dva mcp init                    # Initialize in current directory
dva mcp init --workspace /path  # Initialize in specific path
dva mcp init --force            # Overwrite existing config
```

### `dva mcp add`

Add a new MCP server to the global registry.

**STDIO Server** (command-line process):
```bash
dva mcp add glean \
  --type stdio \
  --command python \
  --args "/path/to/glean_server.py" \
  --env "GLEAN_API_TOKEN=\${GLEAN_API_TOKEN}" \
  --env "GLEAN_DOMAIN=https://company.glean.com" \
  --tools "search_glean,get_document" \
  --description "Glean enterprise search"
```

**HTTP Server** (REST endpoint):
```bash
dva mcp add api-server \
  --type http \
  --url "http://localhost:8000" \
  --tools "query,search"
```

**Docker Server** (Docker Compose):
```bash
dva mcp add kg \
  --type docker \
  --compose ./kg-mcp-infrastructure/docker-compose.yml \
  --service kg-mcp-server \
  --port 8125 \
  --description "Knowledge Graph MCP"
```

**Options:**
| Option | Description |
|--------|-------------|
| `--type, -t` | Server type: `stdio`, `http`, `docker`, `sse` |
| `--name, -n` | Display name |
| `--command, -c` | Command for stdio servers |
| `--args, -a` | Command arguments (comma or space separated) |
| `--url, -u` | URL for HTTP/SSE servers |
| `--compose` | Docker compose file path |
| `--service` | Docker service name |
| `--port, -p` | Port for Docker servers (default: 8125) |
| `--env, -e` | Environment variables (KEY=VALUE) |
| `--tools` | Available tools (comma-separated) |
| `--description, -d` | Server description |
| `--project` | Add to project config instead of global |

### `dva mcp remove`

Remove an MCP server configuration.

```bash
dva mcp remove glean           # Remove with confirmation
dva mcp remove glean --yes     # Skip confirmation
dva mcp remove local --project # Remove from project config
```

### `dva mcp list`

List all configured MCP servers.

```bash
dva mcp list           # List enabled servers
dva mcp list --all     # Include disabled servers
dva mcp list --json    # Output as JSON
```

### `dva mcp show`

Show detailed information about a server.

```bash
dva mcp show kg
```

### `dva mcp start`

Start Docker-based MCP server(s).

```bash
dva mcp start        # Start all Docker servers
dva mcp start kg     # Start specific server
```

### `dva mcp stop`

Stop Docker-based MCP server(s).

```bash
dva mcp stop         # Stop all Docker servers
dva mcp stop kg      # Stop specific server
```

### `dva mcp health`

Check health of MCP server(s).

```bash
dva mcp health           # Check all servers
dva mcp health kg        # Check specific server
dva mcp health --json    # Output as JSON
```

### `dva mcp sync`

Sync MCP configuration to IDE-specific format.

```bash
dva mcp sync --ide windsurf    # Sync to Windsurf
dva mcp sync --ide claude      # Sync to Claude Desktop
dva mcp sync --ide vscode      # Sync to VS Code
dva mcp sync --ide cursor      # Sync to Cursor
dva mcp sync --all             # Sync to all IDEs
dva mcp sync --ide windsurf --global  # Write to global IDE config
```

**Generated files:**
| IDE | Workspace | Global |
|-----|-----------|--------|
| Windsurf | `.windsurf/mcp_config.json` | `~/.codeium/windsurf/mcp_config.json` |
| Claude | `.claude/settings.json` | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| VS Code | `.vscode/settings.json` | `~/.vscode/settings.json` |
| Cursor | `.cursor/mcp.json` | `~/.cursor/mcp.json` |

### `dva mcp import`

Import MCP servers from an existing IDE configuration.

```bash
dva mcp import --from ~/.codeium/windsurf/mcp_config.json --ide windsurf
dva mcp import --from ~/Library/Application\ Support/Claude/claude_desktop_config.json --ide claude
```

### `dva mcp logs`

Show logs from a Docker-based MCP server.

```bash
dva mcp logs kg              # Show last 50 lines
dva mcp logs kg --lines 100  # Show last 100 lines
dva mcp logs kg --follow     # Follow log output
```

## Server Types

### STDIO Servers

Command-line processes that communicate via stdin/stdout.

```bash
dva mcp add my-tool \
  --type stdio \
  --command python \
  --args "server.py,--port,8000" \
  --env "API_KEY=\${MY_API_KEY}"
```

**Examples:**
- Python MCP servers (FastMCP)
- Node.js MCP servers
- Custom CLI tools

### HTTP Servers

REST endpoints that implement MCP protocol.

```bash
dva mcp add api \
  --type http \
  --url "http://localhost:8000/mcp"
```

### Docker Servers

Docker Compose services that expose MCP endpoints.

```bash
dva mcp add kg \
  --type docker \
  --compose ./docker-compose.yml \
  --service mcp-server \
  --port 8125
```

**Benefits:**
- Isolated environment
- Easy start/stop with `dva mcp start/stop`
- Health monitoring
- Log access

### SSE Servers

Server-Sent Events endpoints.

```bash
dva mcp add stream \
  --type sse \
  --url "http://localhost:8000/events"
```

## Environment Variables

Environment variables can reference system variables using `${VAR}` syntax:

```bash
dva mcp add glean \
  --type stdio \
  --command python \
  --args "glean_server.py" \
  --env "GLEAN_API_TOKEN=\${GLEAN_API_TOKEN}" \
  --env "GLEAN_DOMAIN=https://company.glean.com"
```

When syncing to IDE configs, `${VAR}` references are resolved from the current environment.

**Security note:** Sensitive values like API tokens should use environment variable references rather than hardcoded values.

## Project vs Global Configuration

### Global Registry
- Stored in `~/.dva-agentic/mcp/registry.json`
- Available across all workspaces
- Managed with `dva mcp add/remove` (default)

### Project Configuration
- Stored in `.mcp/mcp.json` in workspace
- Can override global settings
- Version-controlled with your project
- Managed with `--project` flag

**Inheritance:**
```json
{
  "inherit_global": true,  // Include global servers
  "servers": {
    "kg": { "enabled": false },  // Disable global server
    "local": { ... }  // Add project-specific server
  }
}
```

Set `"inherit_global": false` to ignore global servers entirely.

## Integration with kg-mcp-infrastructure

The `dva mcp` commands integrate seamlessly with your existing `kg-mcp-infrastructure`:

```bash
# Add KG MCP server
dva mcp add kg \
  --type docker \
  --compose /Users/your-user/dva-agentic-project/kg-mcp-infrastructure/docker-compose.yml \
  --service kg-mcp-server \
  --port 8125 \
  --tools "kg_query,kg_search,kg_stats,kg_ingest" \
  --description "DVA Knowledge Graph MCP"

# Start the server
dva mcp start kg

# Check health
dva mcp health kg

# View logs
dva mcp logs kg --follow

# Sync to Windsurf
dva mcp sync --ide windsurf
```

## Workflow Examples

### Setting Up a New Workspace

```bash
# 1. Initialize MCP config
cd my-project
dva mcp init

# 2. Add servers (if not already in global registry)
dva mcp add kg --type docker --compose ../kg-mcp-infrastructure/docker-compose.yml --port 8125

# 3. Start Docker servers
dva mcp start

# 4. Verify health
dva mcp health

# 5. Sync to IDE
dva mcp sync --ide windsurf
```

### Migrating from IDE-specific Config

```bash
# Import existing Windsurf config
dva mcp import --from ~/.codeium/windsurf/mcp_config.json --ide windsurf

# Review imported servers
dva mcp list

# Now manage with dva mcp commands
dva mcp health
```

### CI/CD Integration

```bash
# In CI pipeline
dva mcp start kg
dva mcp health --json | jq '.healthy'
# Run tests...
dva mcp stop kg
```

## Troubleshooting

### Server Not Starting

```bash
# Check Docker status
docker ps

# Check server logs
dva mcp logs kg

# Verify compose file
cat ./kg-mcp-infrastructure/docker-compose.yml
```

### Health Check Failing

```bash
# Detailed health check
dva mcp health kg --json

# Check if port is in use
lsof -i :8125

# Test endpoint manually
curl http://localhost:8125/health
```

### IDE Not Connecting

1. Verify server is running: `dva mcp health`
2. Check synced config: `cat .windsurf/mcp_config.json`
3. Restart IDE after sync
4. Check IDE logs for MCP errors

### Environment Variables Not Resolved

```bash
# Ensure variables are exported
export GLEAN_API_TOKEN="your-token"

# Re-sync to IDE
dva mcp sync --ide windsurf
```

## Best Practices

1. **Use global registry** for servers shared across projects
2. **Use project config** for project-specific overrides
3. **Use environment variables** for sensitive values
4. **Run `dva mcp health`** before starting work
5. **Sync after changes** with `dva mcp sync --ide <your-ide>`
6. **Version control** `.mcp/mcp.json` with your project
7. **Don't version control** IDE-specific generated files (`.windsurf/`, `.claude/`)

## File Locations

| File | Purpose |
|------|---------|
| `~/.dva-agentic/mcp/registry.json` | Global server registry |
| `.mcp/mcp.json` | Project MCP configuration |
| `.windsurf/mcp_config.json` | Generated Windsurf config |
| `.claude/settings.json` | Generated Claude config |
| `.vscode/settings.json` | Generated VS Code config |
| `.cursor/mcp.json` | Generated Cursor config |
