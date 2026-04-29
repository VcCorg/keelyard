# MCP Gateway

Unified MCP Gateway that aggregates multiple upstream MCP servers behind a **single SSE endpoint**.

## Architecture

```
[AI Client] → :9090/sse → [MCP Gateway]
                               ├── bitbucket_* → bitbucket-mcp:8126
                               ├── jira_*      → jira-mcp:8128
                               └── glean_*     → glean-mcp:8127
```

## Features

- **Single endpoint**: One SSE URL for all tools
- **Dynamic discovery**: Discovers tools from upstream servers at startup
- **Namespaced tools**: `bitbucket_get_pr_overview`, `jira_get_issue`, etc.
- **On-demand connections**: Fresh connection per tool call for resilience
- **Built-in tools**: `gateway_status`, `gateway_refresh`

## Tools

All upstream tools are exposed with `<server>_` prefix:

- `bitbucket_get_pr_overview`, `bitbucket_get_pr_diff`, ...
- `jira_get_issue`, `jira_search_issues`, `jira_get_my_issues`, ...
- `glean_search_glean`, `glean_get_glean_document`, ...
- `gateway_status` — show upstream server config
- `gateway_refresh` — re-discover tools from upstreams

## Configuration

Upstream servers via environment variables:

```bash
MCP_UPSTREAM_BITBUCKET=http://bitbucket-mcp:8126/sse
MCP_UPSTREAM_JIRA=http://jira-mcp:8128/sse
MCP_UPSTREAM_GLEAN=http://glean-mcp:8127/sse
```

## Docker

```bash
docker compose -f mcp-docker-compose.yml up -d mcp-gateway
```

SSE endpoint: `http://localhost:9090/sse`

## Client Configuration

### OpenCode
```json
{"mcp": {"gateway": {"type": "remote", "url": "http://localhost:9090/sse"}}}
```

### Windsurf
```json
{"mcpServers": {"gateway": {"url": "http://localhost:9090/sse", "transport": "sse"}}}
```
