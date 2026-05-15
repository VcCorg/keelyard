# Agentic Platform Central MCP Server

Central MCP server for the Agentic Platform — domain management, onboarding,
skill resolution, and activity tracking for AI coding assistants.

## Tools

| Group | Tool | Purpose |
|-------|------|---------|
| **Products** | `product_create` | Register a product |
| | `product_list` | List products |
| | `product_get` | Get product details |
| **Domains** | `domain_create` | Register a domain under a product |
| | `domain_list` | List domains |
| | `domain_get` | Get domain with repos & docs |
| | `domain_link_repo` | Link a repo to a domain |
| | `domain_unlink_repo` | Unlink a repo |
| | `domain_list_repos` | List repos in a domain |
| | `domain_add_doc` | Track a Confluence doc |
| | `domain_list_docs` | List tracked docs |
| **Repos** | `repo_register` | Register an onboarded repo |
| | `repo_list` | List all onboarded repos |
| | `repo_get` | Get repo details |
| **Activity** | `activity_log` | Record an activity |
| | `activity_recent` | Recent activity log |
| | `activity_summary` | Platform usage summary |
| **Skills** | `registry_list` | List skills in registry |
| | `skill_available` | Check if a skill exists |

## Run locally (stdio)

```bash
pip install -e .
agentic-mcp
```

## Run via Docker (SSE)

```bash
docker build -t agentic-mcp .
docker run -p 8132:8132 -v ~/.agent-cli-agentic:/data agentic-mcp
```

## MCP config

Add to `.windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "agentic": {
      "serverUrl": "http://localhost:8132/sse"
    }
  }
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `stdio` | Transport: `stdio` or `sse` |
| `MCP_PORT` | `8132` | Port for SSE transport |
| `MCP_HOST` | `0.0.0.0` | Host for SSE transport |
| `AGENTIC_TRACKER_DB` | `~/.agent-cli-agentic/tracker.db` | Path to shared tracker database |
| `SKILLS_REGISTRY_PATH` | `../../skills/registry.json` | Path to skills registry |
| `SKILLS_DIR` | `../../skills/skills` | Path to skill SKILL.md directories |
