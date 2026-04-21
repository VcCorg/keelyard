---
name: dva-agentic-platform
description: >-
  Complete context for the DVA Agentic Platform — a multi-repo workspace for building
  AI agent infrastructure. Read this FIRST before any work. Covers all 4 repos,
  9 CLI command groups, 8 MCP servers, knowledge graph, skills registry, and
  Docker infrastructure.
---

# DVA Agentic Platform — Full Context

You are working in a **multi-repo workspace** at `/Users/your-user/dva-agentic-project/` that builds an enterprise AI agent platform. This is NOT a single repo — it contains 4 repos plus workspace-level config.

## Workspace Structure

```
dva-agentic-project/                  ← Workspace root (NOT a repo)
├── dva-agentic-cli/                  ← Repo 1: CLI tool (Python/Typer)
├── dva-skills/                       ← Repo 2: Skills registry (62 skills)
├── dva-mcp-servers/                  ← Repo 3: MCP servers + Docker Compose
├── dva-kg-infrastructure/            ← Repo 4: KG infra (Neo4j, LightRAG)
├── .skills/                          ← THIS context (workspace-level)
├── .windsurf/                        ← Windsurf IDE config
├── .opencode/                        ← OpenCode IDE config
├── docs/LOCAL_DEV_OPS_GUIDE.md       ← Operations guide
└── README.md                         ← Workspace overview
```

## Bitbucket Repos

| Local Dir | Bitbucket Repo | Branch | Clone Command |
|-----------|---------------|--------|---------------|
| `dva-agentic-cli/` | `~your-user/dva-agentic-cli` | develop + feature branches | `git clone https://bitbucket.example.com/scm/~your-user/dva-agentic-cli.git` |
| `dva-skills/` | `~your-user/dva-agent-skills` | develop + feature branches | `git clone https://bitbucket.example.com/scm/~your-user/dva-agent-skills.git dva-skills` |
| `dva-mcp-servers/` | `~your-user/dva-agent-mcp-servers` | develop | `git clone https://bitbucket.example.com/scm/~your-user/dva-agent-mcp-servers.git dva-mcp-servers` |
| `dva-kg-infrastructure/` | `~your-user/dva-agent-kg-infra` | develop | `git clone https://bitbucket.example.com/scm/~your-user/dva-agent-kg-infra.git dva-kg-infrastructure` |

> **Note:** Local dir names differ from Bitbucket slugs. Clone commands use `git clone <url> <local-name>`.

---

## Repo 1: dva-agentic-cli (The CLI)

**Tech stack:** Python 3.10+, Typer, Rich, Pydantic, uv
**Entry point:** `src/dva_agentic_cli/main.py` → registers all Typer sub-apps
**Package:** `dva-agentic-cli`, installed as `dva` command
**Install:** `uv tool install --editable ./dva-agentic-cli` (global) or `uv pip install -e '.'` (venv)

### 9 Command Groups

| Group | File | Purpose | Key Subcommands |
|-------|------|---------|-----------------|
| `dva code` | `commands/code.py` | Onboard repos with AI skills | `onboard`, `skills list\|available\|add\|remove`, `validate`, `config` |
| `dva kg` | `commands/kg.py` | Knowledge graph operations | `init`, `ingest`, `query`, `search`, `stats`, `check`, `clear`, `visualize` |
| `dva data` | `commands/data.py` | Data source management | `init`, `create`, `list`, `show`, `update`, `delete` |
| `dva mcp` | `commands/mcp.py` | MCP server management | `init`, `add`, `remove`, `list`, `health`, `sync`, `start`, `stop` |
| `dva project` | `commands/project.py` | Scaffold agent projects | `create`, `list-templates`, `info` |
| `dva agent` | `commands/agent.py` | Run/manage agents | `run`, `start`, `stop`, `status`, `logs`, `list`, `register` |
| `dva skill` | `commands/skill.py` | Agent Skills (agentskills.io) | `create`, `list`, `install`, `show` |
| `dva init` | `commands/init.py` | Configure Vertex AI, auth | `vertex-ai`, `show`, `reset` |
| `dva history` | `commands/history.py` | Session history tracking | |

### Key Modules

| Module | Path | Purpose |
|--------|------|---------|
| **Analyzer** | `analyzer/detector.py` | Detect language, framework, deps, structure |
| **Matcher** | `analyzer/matcher.py` | Match analysis → registry skills + MCP detection |
| **Templates** | `templates/generator.py` | Scaffold new projects (ADK, PR reviewer, RAG, etc.) |
| **KG** | `kg/` | Neo4j client, parsers, entity extraction, query, search, context builder |
| **MCP** | `mcp/` | Config models, IDE sync, Docker management, health checks |
| **Onboard Agent** | `agents/onboard/` | Modular pipeline: gap detection, skill generation, enrichment |

### Code Onboarding System

The crown jewel: `dva code onboard --path <project>`

1. Analyze project (scan files, parse deps)
2. Match against skills registry (`dva-skills/registry.json`)
3. Detect MCP servers from IDE config
4. Generate `.skills/project-context/SKILL.md` (project-specific context)
5. Install matched skills from registry → `.skills/<name>/`
6. Save `.skills/onboard.json` manifest
7. (Optional) `--agent` flag: AI-powered skill gap detection + generation
8. (Optional) `--kg` flag: Generate KG context + ingest into LightRAG

### Optional Dependencies

```bash
uv tool install --force ./dva-agentic-cli                              # Core only
uv tool install --force ./dva-agentic-cli --with "dva-agentic-cli[kg]" # + KG support
uv tool install --force ./dva-agentic-cli --with "dva-agentic-cli[agent]" # + AI agent
```

### Testing

```bash
cd dva-agentic-cli
make test          # Unit tests with coverage
make lint          # Ruff linting
make format        # Auto-format
```

---

## Repo 2: dva-skills (Skills Registry)

**62 skills** in `registry.json`, each with `auto_detect` rules and a `skills/<name>/SKILL.md`.

Skills cover: Java (Spring Boot, Gradle, Maven), Python (FastAPI, Django, Flask), TypeScript (React, Next.js, Node), Go, testing frameworks, databases (Spanner, Postgres, MongoDB, BigQuery), Docker, CI/CD, GCP, Atlassian MCP, security, APIs, Apache Beam, Kafka Streams, resilience4j, mapstruct, liquibase-spanner, and more.

**Default onboard agent:** `agents/onboard/` — standalone agent project with editable prompts

### Configure
```bash
dva code config --registry /Users/your-user/dva-agentic-project/dva-skills
```

---

## Repo 3: dva-mcp-servers (MCP Servers)

**8 Docker services** in `docker-compose.yml`, all on shared `dva-network`:

| Service | Port | Container | Tools | Connects To |
|---------|------|-----------|-------|-------------|
| **bitbucket-mcp** | 8126 | dva-bitbucket-mcp | 15 (PR review, approve, merge, diff, comments) | Bitbucket Server REST API 1.0 |
| **glean-mcp** | 8127 | dva-glean-mcp | 6 (search, docs, datasources, agents, chat) | Glean REST API v1 |
| **jira-mcp** | 8128 | dva-jira-mcp | 11 (issues, search, comments, transitions, sprints) | Jira Server REST API v2 |
| **confluence-mcp** | 8129 | dva-confluence-mcp | 10 (search, CQL, pages, spaces, comments, labels) | Confluence Server REST API |
| **memory-mcp** | 8130 | dva-memory-mcp | 16 (3 memory types: short-term, long-term, reasoning) | Neo4j (neo4j-agent-memory) |
| **kg-mcp** | 8131 | dva-kg-mcp-new | 8 (search context, query, entity details, manage sources) | Neo4j + LightRAG |
| **mcp-gateway** | 9090 | dva-mcp-gateway | Aggregates all upstream tools (namespaced) | All above services |
| **mcp-proxy** | 9091 | dva-mcp-proxy | Named server proxy (path-based) | bitbucket + jira (stdio) |

### Architecture Pattern (all servers follow)

```
src/<pkg>/
  __init__.py
  config.py          ← pydantic-settings
  <name>_client.py   ← httpx client
  server.py          ← FastMCP server
pyproject.toml       ← hatchling build
Dockerfile           ← python:3.12-slim
```

- Dual transport: `stdio` (local dev) / `sse` (Docker) via `MCP_TRANSPORT` env var
- Auth: Bearer PAT for all Atlassian services
- SSE healthcheck: `curl --max-time 2` (exit 28 = connected = healthy)

### Start/Stop

```bash
cd dva-mcp-servers
cp .env.example .env      # Fill in tokens
docker network create dva-network  # One-time
docker compose up -d       # Start all
docker compose down        # Stop all
```

### Required Tokens (.env)

- `BITBUCKET_PERSONAL_ACCESS_TOKEN` — Bitbucket Server PAT
- `JIRA_PERSONAL_ACCESS_TOKEN` — Jira Server PAT
- `CONFLUENCE_PERSONAL_ACCESS_TOKEN` — Confluence Server PAT
- `GLEAN_API_TOKEN` — Glean API token
- `NEO4J_PASSWORD` — Neo4j database password

---

## Repo 4: dva-kg-infrastructure (Knowledge Graph)

```
dva-kg-infrastructure/
├── kg-mcp/       ← Original KG MCP (FastAPI HTTP, port 8125) — legacy
├── neo4j/        ← Neo4j 5.14 with APOC, docker-compose
├── lightrag/     ← LightRAG server, docker-compose
├── data/cwow/    ← Sample data
└── docs/         ← Architecture docs, cleanup audit
```

### Start Infrastructure
```bash
cd dva-kg-infrastructure/neo4j && docker compose up -d    # Neo4j on 7474/7687
cd dva-kg-infrastructure/lightrag && docker compose up -d  # LightRAG on 8001
```

### Important: Namespace Scoping
Neo4j is shared between `memory-mcp` and `kg` commands. All KG data is scoped with `_source='dva_kg'` property to avoid collisions. The `dva kg clear` command only deletes KG-scoped nodes.

---

## MCP Server Configuration for AI Tools

### Windsurf
Config: `.windsurf/mcp_config.json` (workspace-level)

### OpenCode
Config: `.opencode/mcp.json` (workspace-level) or `~/.config/opencode/config.json` (global)
Format: `"mcp"` key (not `"mcpServers"`), `type: "remote"` for SSE

### Claude Code
Reads `.skills/` directory automatically (agentskills.io standard)
MCP: `CLAUDE.md` at workspace root + `.mcp.json`

### All SSE Endpoints
```
http://localhost:8126/sse   ← Bitbucket (PR tools)
http://localhost:8127/sse   ← Glean (enterprise search)
http://localhost:8128/sse   ← Jira (issue tracking)
http://localhost:8129/sse   ← Confluence (wiki/docs)
http://localhost:8130/sse   ← Memory (agent memory, 3 types)
http://localhost:8131/sse   ← KG (knowledge graph, business context)
http://localhost:9090/sse   ← Gateway (all tools aggregated)
```

---

## Configuration Files

| File | Purpose |
|------|---------|
| `~/.dva-agentic/config.json` | CLI config (Vertex AI, data sources) |
| `~/.dva-agentic/kg-config.json` | KG provider config (Neo4j URI, LightRAG URL) |
| `~/.dva-agentic/mcp/registry.json` | MCP server registry |
| `dva-mcp-servers/.env` | Docker environment (tokens, URLs) |
| `.windsurf/mcp_config.json` | Windsurf MCP connections |
| `.opencode/mcp.json` | OpenCode MCP connections |

---

## Port Map

| Port | Service | Protocol |
|------|---------|----------|
| 7474 | Neo4j Browser | HTTP |
| 7687 | Neo4j Bolt | Bolt |
| 8001 | LightRAG API | HTTP |
| 8125 | KG MCP (legacy) | HTTP |
| 8126 | Bitbucket MCP | SSE |
| 8127 | Glean MCP | SSE |
| 8128 | Jira MCP | SSE |
| 8129 | Confluence MCP | SSE |
| 8130 | Memory MCP | SSE |
| 8131 | KG MCP (new) | SSE |
| 9090 | MCP Gateway | SSE |
| 9091 | MCP Proxy | SSE |

---

## Key Workflows

### Full Environment Startup
```bash
# 1. Start infrastructure
cd dva-kg-infrastructure/neo4j && docker compose up -d && cd ../..
cd dva-mcp-servers && docker compose up -d && cd ..

# 2. Verify
dva --version
dva kg check
docker compose -f dva-mcp-servers/docker-compose.yml ps
```

### Onboard a New Project
```bash
dva code config --registry ./dva-skills
dva code onboard --path /path/to/project
dva code onboard --path /path/to/project --agent      # With AI gap detection
dva code onboard --path /path/to/project --kg          # With KG context
```

### Ingest Data into Knowledge Graph
```bash
dva data create --name my-docs --source-type doc --source-location /path/to/docs
dva kg ingest --source my-docs
dva kg ingest --path /path/to/file.pdf
dva kg query "Find all entities related to patient care"
```

### Create a New Agent Project
```bash
dva project create my-agent --use-case pr-reviewer --jira-mcp
dva project create my-rag --use-case rag
dva project create my-kg --use-case knowledge-graph
```

---

## Key Design Decisions

1. **Multi-repo workspace** — Each concern in its own repo for independent versioning
2. **Skills as portable files** — `.skills/<name>/SKILL.md` works across all AI tools (agentskills.io standard)
3. **MCP servers as Docker services** — Dual transport (stdio/sse), shared `dva-network`
4. **Neo4j namespace scoping** — `_source='dva_kg'` prevents collision with memory-mcp
5. **KG MCP rebuilt** — Moved from custom FastAPI (port 8125) to proper FastMCP SSE (port 8131) in dva-mcp-servers
6. **Onboard agent decoupled** — Library (in CLI) + standalone agent (in skills registry) + template (via `dva project create`)
7. **uv tool install** — CLI runs globally from any directory, independent of venv

---

## Files to Read First (by area)

### CLI Development
1. `dva-agentic-cli/docs/AGENT_DEVELOPMENT.md`
2. `dva-agentic-cli/src/dva_agentic_cli/main.py`
3. `dva-agentic-cli/pyproject.toml`

### Code Onboarding
1. `dva-agentic-cli/src/dva_agentic_cli/commands/code.py`
2. `dva-agentic-cli/src/dva_agentic_cli/analyzer/detector.py`
3. `dva-agentic-cli/src/dva_agentic_cli/analyzer/matcher.py`
4. `dva-skills/registry.json`

### MCP Servers
1. `dva-mcp-servers/docker-compose.yml`
2. `dva-mcp-servers/.env.example`
3. Any `dva-mcp-servers/<service>/src/*/server.py`

### Knowledge Graph
1. `dva-agentic-cli/src/dva_agentic_cli/commands/kg.py`
2. `dva-agentic-cli/src/dva_agentic_cli/kg/ingest.py`
3. `dva-kg-infrastructure/docs/CLEANUP_AUDIT.md`

### Operations
1. `docs/LOCAL_DEV_OPS_GUIDE.md` (comprehensive setup + troubleshooting)
