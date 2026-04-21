# DVA MCP Servers

Model Context Protocol (MCP) servers for AI code assistants. Provides Bitbucket, Jira, Confluence, Glean, and gateway services via SSE endpoints.

## Architecture

```
dva-mcp-servers/
├── bitbucket/          # Bitbucket Server PR review tools (port 8126)
├── glean/              # Glean enterprise search & AI assistants (port 8127)
├── jira/               # Jira Server issue tracking tools (port 8128)
├── confluence/         # Confluence Server wiki & docs tools (port 8129)
├── gateway/            # Unified MCP gateway aggregating all upstream servers (port 9090)
├── proxy/              # Alternative mcp-proxy named server config (port 9091)
├── docker-compose.yml  # Orchestrates all services
└── .env.example        # Environment variables template
```

## Quick Start

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your tokens

# Create Docker network (first time only)
docker network create dva-network

# Start all services
docker compose up -d

# Start specific services
docker compose up -d bitbucket-mcp jira-mcp

# Check health
docker compose ps
```

## Services

| Service | Port | SSE Endpoint | Description |
|---------|------|-------------|-------------|
| bitbucket-mcp | 8126 | `http://localhost:8126/sse` | 15 tools: PR overview, diff, files, commits, comments, activities, approve, merge, etc. |
| glean-mcp | 8127 | `http://localhost:8127/sse` | 6 tools: search, documents, datasources, agents, chat, conversations |
| jira-mcp | 8128 | `http://localhost:8128/sse` | 11 tools: issues, search, comments, transitions, assignments, sprints, projects |
| confluence-mcp | 8129 | `http://localhost:8129/sse` | 10 tools: search, pages, spaces, child pages, comments, labels, CQL queries |
| mcp-gateway | 9090 | `http://localhost:9090/sse` | Aggregates all upstream servers behind single endpoint |
| mcp-proxy | 9091 | `http://localhost:9091/servers/<name>/sse` | Named server proxy |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BITBUCKET_SERVER_URL` | Yes | Bitbucket Server URL |
| `BITBUCKET_PERSONAL_ACCESS_TOKEN` | Yes | Bitbucket PAT |
| `JIRA_SERVER_URL` | Yes | Jira Server URL |
| `JIRA_PERSONAL_ACCESS_TOKEN` | Yes | Jira PAT |
| `GLEAN_API_TOKEN` | No | Glean API token |
| `GLEAN_DOMAIN` | No | Glean domain URL |
| `CONFLUENCE_SERVER_URL` | No | Confluence Server URL |
| `CONFLUENCE_PERSONAL_ACCESS_TOKEN` | No | Confluence PAT |

## IDE Configuration

### Windsurf (`.windsurf/mcp_config.json`)

```json
{
  "mcpServers": {
    "bitbucket": {
      "serverUrl": "http://localhost:8126/sse"
    },
    "jira": {
      "serverUrl": "http://localhost:8128/sse"
    },
    "confluence": {
      "serverUrl": "http://localhost:8129/sse"
    }
  }
}
```

### OpenCode (`~/.config/opencode/config.json`)

```json
{
  "mcp": {
    "bitbucket": { "type": "remote", "url": "http://localhost:8126/sse" },
    "jira": { "type": "remote", "url": "http://localhost:8128/sse" },
    "confluence": { "type": "remote", "url": "http://localhost:8129/sse" }
  }
}
```

## Related Repos

- [dva-agentic-cli](https://bitbucket.example.com/users/your-user/repos/dva-agentic-cli) — CLI tool that uses these MCP servers for agent workflows
- [dva-agent-skills](https://bitbucket.example.com/users/your-user/repos/dva-agent-skills) — Skills registry with MCP-backed skills (jira, bitbucket, pr-reviewer)
- [dva-agent-kg-infra](https://bitbucket.example.com/users/your-user/repos/dva-agent-kg-infra) — Knowledge Graph MCP server + Neo4j + LightRAG
