# Jira Server MCP

Model Context Protocol server for **Jira Server/Data Center** — exposes issue tracking tools for AI assistants.

## Tools

| Tool | Description |
|------|-------------|
| `get_issue` | Get detailed issue info (status, assignee, subtasks, links) |
| `search_issues` | Search issues using JQL |
| `get_my_issues` | Get issues assigned to current user |
| `get_comments` | Get all comments on an issue |
| `add_comment` | Add a comment to an issue |
| `get_transitions` | Get available workflow transitions |
| `transition_issue` | Move issue to a new status |
| `assign_issue` | Assign issue to a user |
| `list_projects` | List all visible projects |
| `get_sprint_issues` | Get issues in active sprint |
| `get_jira_config` | Show connection config (debug) |

## Setup

### Environment Variables

```bash
export JIRA_SERVER_URL=https://jira.example.com
export JIRA_PERSONAL_ACCESS_TOKEN=your-token-here
# Optional
export JIRA_DEFAULT_PROJECT=CWHE
```

### Docker (SSE transport)

```bash
docker compose -f mcp-docker-compose.yml up -d jira-mcp
```

SSE endpoint: `http://localhost:8128/sse`

### Local (stdio transport)

```bash
cd jira-server-mcp
python -m venv .venv && source .venv/bin/activate
pip install -e .
JIRA_SERVER_URL=https://jira.example.com \
JIRA_PERSONAL_ACCESS_TOKEN=your-token \
python -m jira_server_mcp.server
```

## Client Configuration

### OpenCode (`~/.config/opencode/config.json`)
```json
{
  "mcp": {
    "jira": {
      "type": "remote",
      "url": "http://localhost:8128/sse"
    }
  }
}
```

### Windsurf (`.windsurf/mcp_config.json`)
```json
{
  "mcpServers": {
    "jira": {
      "url": "http://localhost:8128/sse",
      "transport": "sse"
    }
  }
}
```
