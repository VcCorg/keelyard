# DVA Knowledge Graph MCP Server

MCP server providing business context, requirements search, and domain knowledge tools for AI coding assistants.

## Tools

| Tool | Purpose | Primary User |
|------|---------|-------------|
| `search_business_context` | Search business rules and requirements | AI assistants |
| `get_project_context` | Project overview and domain summary | AI assistants |
| `query_knowledge_graph` | Structured/Cypher queries, persona filtering | AI assistants |
| `get_entity_details` | Drill into entity + relationships | AI assistants |
| `list_knowledge_projects` | Discover available projects | Both |
| `register_knowledge_source` | Register a doc dir or Confluence space | Humans |
| `remove_knowledge_source` | Remove a registered source | Humans |
| `ingest_knowledge_source` | Index a registered source into KG | Humans |

## Source Types

- **document** — Local directory of `.pdf`, `.md`, `.txt`, `.json`, `.csv` files
- **confluence** — Confluence Server space (requires `CONFLUENCE_PERSONAL_ACCESS_TOKEN`)

## Quick Start

```bash
# Local (stdio)
cd kg && pip install -e .
kg-mcp

# Docker (SSE)
docker compose up kg-mcp
# SSE endpoint: http://localhost:8131/sse
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `KG_NEO4J_URI` | `bolt://dva-neo4j:7687` | Neo4j connection |
| `KG_NEO4J_USER` | `neo4j` | Neo4j username |
| `KG_NEO4J_PASSWORD` | | Neo4j password |
| `KG_LIGHTRAG_URL` | `http://dva-lightrag:8001` | LightRAG REST API |
| `KG_DEFAULT_PROVIDER` | `lightrag` | Default backend |
| `KG_SOURCE_REGISTRY_PATH` | `/data/kg-sources.json` | Source registry file |
| `CONFLUENCE_PERSONAL_ACCESS_TOKEN` | | For Confluence ingestion |
