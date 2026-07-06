# Agentic Platform — Workspace

Multi-repo workspace for the Agentic platform. Each component lives in its own Git repo.

## Repos

| Local Dir | Description |
|-----------|-------------|
| `agentic-cli/` | CLI tool — agent, skill, code onboard, kg, mcp, project commands |
| `skills/` | Skills registry — skill definitions and AI evaluation framework |
| `mcp-servers/` | MCP servers — multiple protocol implementations + docker-compose |
| `kg-infrastructure/` | KG infra — knowledge graph server, Neo4j, LightRAG, sample data, docs |

## Preventing internal/company data in commits

This repo ships a guard that blocks commits containing company-specific data
(internal hostnames, usernames), real domain/KG data files, and secret formats.

Enable the version-controlled hook once per clone:

```bash
git config core.hooksPath .githooks
```

- Manual scan of the whole tree (also used in CI): `bash scripts/check-no-company-data.sh --all`
- The pre-commit hook scans only staged changes automatically.
- Real domain data (`skills/domains/cwow-*/`, `kg-infrastructure/docs/CWOW_*|SNF_*`,
  `graphify-out/`, `knowledge-export/`) is git-ignored and stays local.
- Emergency bypass (discouraged): `ALLOW_COMPANY_DATA=1 git commit ...`

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

**Prerequisites:** [`uv`](https://docs.astral.sh/uv/) (Python 3.12), and Docker (optional, for MCP/KG infrastructure).

```bash
# 1. Clone the repo
git clone <your-fork-or-repo-url> agentic-project
cd agentic-project

# 2. One-shot setup: installs the CLI, configures the skills registry,
#    bootstraps mcp-servers/.env, and runs preflight diagnostics.
./setup.sh                 # add --with-mcp to also start the MCP Docker stack

# 3. Activate the project venv
source .venv/bin/activate

# 4. Configure integration credentials in mcp-servers/.env
#    (set *_SERVER_URL and *_PERSONAL_ACCESS_TOKEN for Bitbucket/Jira/Confluence)

# 5. Verify your environment anytime
keel doctor                 # add --probe to test host reachability

# 6. Onboard any project
keel code onboard --path ./some-project
```

### Manual setup (if you prefer step-by-step)

```bash
./install-agentic-cli.sh --project --native-tls   # install CLI into ./.venv
source .venv/bin/activate
keel code config --registry ./skills                # configure skills registry
cp mcp-servers/.env.example mcp-servers/.env       # then edit with your URLs/tokens
cd mcp-servers && docker compose up -d && cd ..    # start MCP servers
keel doctor                                         # validate everything
```

> All base URLs are configuration-driven. Set `BITBUCKET_SERVER_URL`,
> `JIRA_SERVER_URL`, and `CONFLUENCE_SERVER_URL` (with matching
> `*_PERSONAL_ACCESS_TOKEN`s) via `mcp-servers/.env` — there are no
> vendor-specific defaults baked into the code.

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
