# Glean MCP Server

MCP server for Glean enterprise search and AI assistant integration. Provides tools for AI assistants to search across enterprise knowledge, retrieve documents, and interact with Glean agents.

## Tools

| Tool | Description |
|------|-------------|
| `search_glean` | Search across Glean datasources for documents and content |
| `get_glean_document` | Retrieve a specific document by ID |
| `list_glean_datasources` | List all available datasources |
| `list_glean_agents` | List available Glean agents/assistants |
| `chat_with_glean_agent` | Send a message to a Glean agent |
| `get_glean_conversation` | Retrieve conversation history |

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `GLEAN_API_TOKEN` | Yes | Glean API bearer token |
| `GLEAN_DOMAIN` | Yes | Glean instance URL (e.g. `https://example-production-be.glean.com`) |
| `GLEAN_BASE_URL` | No | Override the full API base URL |

## Usage

### Local (stdio)
```bash
pip install -e .
GLEAN_API_TOKEN=xxx GLEAN_DOMAIN=https://your-instance.glean.com glean-mcp
```

### Docker (SSE)
```bash
docker compose up -d glean-mcp
# SSE endpoint: http://localhost:8127/sse
```

## Architecture

```
glean/
├── src/glean_mcp/
│   ├── __init__.py
│   ├── config.py          # Pydantic settings (env-based)
│   ├── glean_client.py    # Async httpx client for Glean REST API
│   └── server.py          # FastMCP server with tool definitions
├── Dockerfile
├── pyproject.toml
└── README.md
```
