# Confluence MCP Server

MCP server for Confluence Server/Data Center. Provides tools for AI assistants to search wiki pages, read documentation, browse spaces, and interact with Confluence content.

## Tools

| Tool | Description |
|------|-------------|
| `search_confluence` | Search pages by text with optional space/type filters |
| `search_confluence_cql` | Advanced search using raw CQL queries |
| `get_confluence_page` | Get a page by ID or by space key + title |
| `list_confluence_spaces` | List available spaces (global/personal) |
| `get_confluence_space` | Get details of a specific space |
| `get_child_pages` | Get child pages of a parent page |
| `get_space_pages` | Get all pages in a space |
| `get_page_comments` | Get comments on a page |
| `add_confluence_comment` | Add a comment to a page |
| `get_page_labels` | Get labels on a page |

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `CONFLUENCE_SERVER_URL` | Yes | Confluence Server URL (e.g. `https://confluence.example.com`) |
| `CONFLUENCE_PERSONAL_ACCESS_TOKEN` | Yes | Confluence PAT for authentication |
| `CONFLUENCE_DEFAULT_SPACE` | No | Default space key for searches |

## Usage

### Local (stdio)
```bash
pip install -e .
CONFLUENCE_SERVER_URL=https://confluence.example.com \
CONFLUENCE_PERSONAL_ACCESS_TOKEN=xxx \
confluence-mcp
```

### Docker (SSE)
```bash
docker compose up -d confluence-mcp
# SSE endpoint: http://localhost:8129/sse
```

## CQL Examples

```
# Pages containing "deployment" in DEV space
space=DEV AND type=page AND text~"deployment"

# Recently modified pages
type=page AND lastModified > now("-7d") ORDER BY lastModified DESC

# Pages with specific label
type=page AND label=api

# Pages by author
type=page AND creator=your-user
```

## Architecture

```
confluence/
├── src/confluence_mcp/
│   ├── __init__.py
│   ├── config.py              # Pydantic settings (env-based)
│   ├── confluence_client.py   # Sync httpx client for Confluence REST API
│   └── server.py              # FastMCP server with tool definitions
├── Dockerfile
├── pyproject.toml
└── README.md
```
