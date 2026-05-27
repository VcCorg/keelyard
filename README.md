# Agentic Platform — Workspace

Multi-repo workspace for the Agentic platform. Each component lives in its own Git repo.

## Repos

| Local Dir | Description |
|-----------|-------------|
| `agentic-cli/` | CLI tool — agent, skill, code onboard, kg, mcp, project commands |
| `skills/` | Skills registry — skill definitions and AI evaluation framework |
| `mcp-servers/` | MCP servers — multiple protocol implementations + docker-compose |
| `kg-infrastructure/` | KG infra — knowledge graph server, Neo4j, LightRAG, sample data, docs |

## Workspace Layout

```
agentic-project/              ← This workspace (not a repo itself)
├── agentic-cli/              ← Repo 1: CLI tool
├── skills/                   ← Repo 2: Skills registry
├── mcp-servers/              ← Repo 3: MCP servers (consolidated)
├── kg-infrastructure/        ← Repo 4: KG infrastructure (consolidated)
├── agent-templates/          ← Reference templates
├── agent-tools/              ← Reusable tools library
├── dashboard/                ← Web UI for platform
├── .windsurf/                ← Local IDE config (not in any repo)
└── README.md                 ← This file
```

## Quick Start

```bash
# Clone all repos into workspace
mkdir agentic-project && cd agentic-project
git clone <repo-url>/agentic-cli.git
git clone <repo-url>/agent-skills.git skills
git clone <repo-url>/agent-mcp-servers.git mcp-servers
git clone <repo-url>/agent-kg-infra.git kg-infrastructure

# Install CLI (uses project-level uv venv with Python 3.12)
./install-agentic-cli.sh --project --native-tls

# Activate project venv
source .venv/bin/activate

# Configure skills registry
dva code config --registry ./skills

# Start MCP servers
cd mcp-servers && cp .env.example .env && docker compose up -d && cd ..

# Onboard any project
dva code onboard --path ./some-project
```

## Development

### Project Virtual Environment

This workspace uses a single project-level uv venv at `.venv` (Python 3.12) for all Python components:

- **agentic-cli** — CLI tool
- **dashboard/backend** — FastAPI backend

To activate:
```bash
source .venv/bin/activate
```

### Running the Dashboard

```bash
# Start backend (uses project venv)
./start-backend.sh

# Start frontend (in another terminal)
./start-frontend.sh
```

The dashboard will be available at:
- Backend: http://localhost:8000
- Frontend: http://localhost:5173

## Dependencies Between Repos

```
agentic-cli ──uses──→ skills (skills registry)
agentic-cli ──uses──→ mcp-servers (MCP tools for agents)
agentic-cli ──uses──→ kg-infrastructure (kg commands)
mcp-servers ──refs──→ kg-infrastructure (kg-mcp in compose)
skills ────no deps────
```
