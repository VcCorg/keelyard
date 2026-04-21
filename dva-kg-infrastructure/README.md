# DVA Knowledge Graph Infrastructure

Docker-based infrastructure for the DVA Knowledge Graph system — Neo4j graph database, LightRAG retrieval-augmented generation, and KG MCP server.

## Architecture

```
dva-kg-infrastructure/
├── kg-mcp/             # KG MCP server (port 8125) — exposes KG tools to AI assistants
├── neo4j/              # Neo4j graph database Docker setup (ports 7474, 7687)
├── lightrag/           # LightRAG service Docker setup (port 8001)
├── data/               # Sample datasets (CWOW patient/facility)
└── docs/               # Infrastructure and analysis documentation
```

## Quick Start

```bash
# Start Neo4j
cd neo4j
docker compose up -d

# Start LightRAG
cd lightrag
docker compose up -d

# Start KG MCP server (from dva-mcp-servers docker-compose or standalone)
cd kg-mcp
docker compose up -d
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Neo4j | 7474 (HTTP), 7687 (Bolt) | Graph database for entity/relationship storage |
| LightRAG | 8001 | RAG service with graph-enhanced retrieval |
| KG MCP | 8125 | MCP server exposing KG operations to IDE tools |

## Data

Sample CWOW (Clinical Workflow) datasets in `data/`:
- `data/cwow/patient/` — Patient-related data
- `data/cwow/facility/` — Facility data
- `data/cwow/apoc/` — APOC graph procedures

## Documentation

- `docs/CWOW_CENSUS_LIST_DATABASE_TABLES.md` — Database table reference
- `docs/CWOW_CENSUS_LIST_USE_CASES.md` — Use case documentation
- `docs/KG_VERSIONING_IMPLEMENTATION_PLAN.md` — Versioning design
- `docs/LIGHTRAG_DATA_VALIDATION.md` — LightRAG validation
- `docs/INFRASTRUCTURE_VALIDATION_SUMMARY.md` — Infrastructure validation

## Integration with dva CLI

```bash
# Configure KG
dva kg init --provider neo4j --uri bolt://localhost:7687

# Ingest data
dva kg ingest --path data/cwow/patient/

# Query
dva kg query "Find all patients"

# Visualize
dva kg visualize --output graph.html
```

## Related Repos

- [dva-agentic-cli](https://bitbucket.example.com/users/your-user/repos/dva-agentic-cli) — CLI with `dva kg` commands for KG operations
- [dva-agent-mcp-servers](https://bitbucket.example.com/users/your-user/repos/dva-agent-mcp-servers) — MCP docker-compose references kg-mcp for unified stack
- [dva-agent-skills](https://bitbucket.example.com/users/your-user/repos/dva-agent-skills) — Skills registry with database-spanner and other data skills
