# DVA Agentic Platform — Local Development Operations Guide

This guide covers setting up, running, and maintaining the DVA Agentic platform locally for development.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Workspace Setup](#workspace-setup)
- [Installing the CLI Globally](#installing-the-cli-globally)
- [MCP Servers](#mcp-servers)
- [Knowledge Graph Infrastructure](#knowledge-graph-infrastructure)
- [Skills Registry](#skills-registry)
- [Development Workflow](#development-workflow)
- [Common Operations](#common-operations)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Tool | Install | Verify |
|------|---------|--------|
| Python 3.10+ | `brew install python@3.12` | `python3 --version` |
| uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `uv --version` |
| Docker Desktop | [docker.com](https://www.docker.com/products/docker-desktop/) | `docker --version` |
| Git | `brew install git` | `git --version` |
| gcloud CLI | `brew install google-cloud-sdk` | `gcloud --version` |

Ensure `~/.local/bin` is on your PATH (uv tool installs go here):

```bash
# Add to ~/.zshrc or ~/.bashrc if not already present
export PATH="$HOME/.local/bin:$PATH"
```

---

## Workspace Setup

### 1. Clone All Repos

```bash
mkdir dva-agentic-project && cd dva-agentic-project

git clone https://bitbucket.example.com/scm/~your-user/dva-agentic-cli.git
git clone https://bitbucket.example.com/scm/~your-user/dva-agent-skills.git dva-skills
git clone https://bitbucket.example.com/scm/~your-user/dva-agent-mcp-servers.git dva-mcp-servers
git clone https://bitbucket.example.com/scm/~your-user/dva-agent-kg-infra.git dva-kg-infrastructure
```

### 2. Workspace Layout

```
dva-agentic-project/              ← Workspace root (not a repo)
├── dva-agentic-cli/              ← CLI tool (Python/Typer)
├── dva-skills/                   ← Skills registry (26 SKILL.md files)
├── dva-mcp-servers/              ← MCP servers + Docker Compose
│   ├── bitbucket/                ← Bitbucket Server MCP (port 8126)
│   ├── jira/                     ← Jira Server MCP (port 8128)
│   ├── gateway/                  ← Unified MCP gateway (port 9090)
│   ├── proxy/                    ← mcp-proxy alternative (port 9091)
│   └── docker-compose.yml
├── dva-kg-infrastructure/        ← Knowledge graph infra
│   ├── kg-mcp/                   ← KG MCP server (port 8125)
│   ├── neo4j/                    ← Neo4j database
│   ├── lightrag/                 ← LightRAG server
│   └── data/                     ← Sample data
├── .windsurf/                    ← IDE config (local only)
└── README.md
```

### 3. Dependencies Between Repos

```
dva-agentic-cli ──uses──→ dva-skills          (skills registry)
dva-agentic-cli ──uses──→ dva-mcp-servers     (MCP tools for agents)
dva-agentic-cli ──uses──→ dva-kg-infrastructure (kg commands)
dva-mcp-servers ──refs──→ dva-kg-infrastructure (kg-mcp in compose)
```

---

## Installing the CLI Globally

The `dva` command is installed as a global tool via **uv tool**, similar to how `opencode` or `pipx`-installed tools work. It runs from any directory, independent of conda/venv environments.

### First-Time Install

```bash
uv tool install ./dva-agentic-cli
```

This builds a wheel from source and installs it to `~/.local/bin/dva` in an isolated Python environment.

### Verify

```bash
which dva          # → ~/.local/bin/dva
dva --version      # → dva-agentic-cli version 0.1.0
```

### Updating After Code Changes

`uv tool install` creates a **snapshot** — it is not editable. After modifying code in `dva-agentic-cli/`, re-install:

```bash
# Re-install from local source (force overwrites existing)
uv tool install --force ./dva-agentic-cli

# Or upgrade if version bumped
uv tool upgrade dva-agentic-cli
```

### Editable Install (Alternative)

If you want live changes reflected without re-installing:

```bash
uv tool install --editable ./dva-agentic-cli
```

> **Note:** Editable mode is convenient during active development but slightly slower at startup.

### Managing the Tool

```bash
uv tool list                          # List all uv-managed tools
uv tool uninstall dva-agentic-cli     # Remove global install
uv tool install --force ./dva-agentic-cli  # Reinstall from source
```

### Installing with Optional Dependencies

The CLI has optional dependency groups for extended features:

```bash
# With knowledge graph support (Neo4j, Vertex AI, PDF parsing, etc.)
uv tool install --force ./dva-agentic-cli --with "dva-agentic-cli[kg]"

# With all features
uv tool install --force ./dva-agentic-cli --with "dva-agentic-cli[kg,dev]"
```

---

## MCP Servers

MCP (Model Context Protocol) servers provide tool access to AI agents (Windsurf, OpenCode, Claude Desktop).

### Services

| Service | Port | Container | Endpoint |
|---------|------|-----------|----------|
| Bitbucket MCP | 8126 | dva-bitbucket-mcp | `http://localhost:8126/sse` |
| Glean MCP | 8127 | dva-glean-mcp | `http://localhost:8127/sse` |
| Jira MCP | 8128 | dva-jira-mcp | `http://localhost:8128/sse` |
| MCP Gateway | 9090 | dva-mcp-gateway | `http://localhost:9090/sse` |
| MCP Proxy | 9091 | dva-mcp-proxy | `http://localhost:9091/servers/*/sse` |
| KG MCP | 8125 | (in kg-infra) | `http://localhost:8125` |

### Setup

```bash
cd dva-mcp-servers

# Create Docker network (one-time)
docker network create dva-network

# Create .env from template
cp .env.example .env
```

### Configure Tokens

Edit `dva-mcp-servers/.env` and fill in the required tokens **before** starting any services:

```bash
# ── Bitbucket MCP ──────────────────────────────────────────
BITBUCKET_SERVER_URL=https://bitbucket.example.com
BITBUCKET_PERSONAL_ACCESS_TOKEN=<your-bitbucket-pat>

# ── Jira MCP ───────────────────────────────────────────────
JIRA_SERVER_URL=https://jira.example.com
JIRA_PERSONAL_ACCESS_TOKEN=<your-jira-pat>

# ── Glean MCP ──────────────────────────────────────────────
GLEAN_API_TOKEN=<your-glean-api-token>
GLEAN_DOMAIN=https://example-production-be.glean.com

# ── KG MCP (used by dva-kg-infrastructure) ─────────────────
KG_PROVIDER=neo4j
NEO4J_URI=bolt://dva-neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=changeme
```

#### How to Generate Tokens

**Bitbucket Personal Access Token:**
1. Go to https://bitbucket.example.com → click your avatar → **Manage account**
2. Navigate to **Personal access tokens** → **Create a token**
3. Name: `dva-mcp` (or any label)
4. Permissions: **Repository Read** (minimum), **Repository Write** for PR actions
5. Copy the token and paste it as `BITBUCKET_PERSONAL_ACCESS_TOKEN` in `.env`

**Jira Personal Access Token:**
1. Go to https://jira.example.com → click your avatar → **Profile**
2. Navigate to **Personal Access Tokens** → **Create token**
3. Name: `dva-mcp` (or any label)
4. Copy the token and paste it as `JIRA_PERSONAL_ACCESS_TOKEN` in `.env`

**Glean API Token:**
1. Contact your Glean admin or generate from the Glean admin console
2. Paste it as `GLEAN_API_TOKEN` in `.env`

> **Security:** The `.env` file is git-ignored. Never commit tokens to the repository.

#### Verify Tokens Are Set

```bash
# Quick check — should show values, not placeholders
grep -E '(TOKEN|PASSWORD)=' dva-mcp-servers/.env | sed 's/=.*/=***/'
```

### Start / Stop

```bash
# Start all MCP servers
docker compose up -d

# Start specific servers only
docker compose up -d bitbucket-mcp jira-mcp

# Stop all
docker compose down

# View logs
docker compose logs -f bitbucket-mcp
docker compose logs -f --tail=50
```

### Health Check

```bash
# Check container status
docker compose ps

# Test SSE endpoints (curl will timeout after connecting — that's healthy)
curl --max-time 2 http://localhost:8126/sse  # Bitbucket
curl --max-time 2 http://localhost:8128/sse  # Jira
curl --max-time 2 http://localhost:9090/sse  # Gateway
```

### Rebuild After Code Changes

```bash
# Rebuild a single service
docker compose build bitbucket-mcp
docker compose up -d bitbucket-mcp

# Rebuild all
docker compose build
docker compose up -d
```

---

## Knowledge Graph Infrastructure

### Neo4j

```bash
cd dva-kg-infrastructure/neo4j
./setup.sh                    # Start Neo4j container

# Or manually:
docker compose up -d
```

- **Browser UI:** http://localhost:7474
- **Bolt:** bolt://localhost:7687
- **Default auth:** neo4j / password

### LightRAG

```bash
cd dva-kg-infrastructure/lightrag
./setup.sh                    # Start LightRAG server
```

- **API:** http://localhost:8001

### Configure KG in CLI

```bash
# LightRAG (simpler)
dva kg init --provider lightrag --lightrag-url http://localhost:8001

# Neo4j (advanced graph operations)
dva kg init --provider neo4j --uri bolt://localhost:7687 --username neo4j --password password

# Check prerequisites
dva kg check

# Ingest data
dva kg ingest --path /path/to/documents
dva kg ingest --source my-data-source

# Query
dva kg query "Find all entities related to patient care"
dva kg stats
```

---

## Skills Registry

The skills registry provides AI code assist skills for project onboarding.

### Configure

```bash
dva code config --registry /path/to/dva-skills
```

### Onboard a Project

```bash
dva code onboard --path /path/to/project
```

This analyzes the project, matches skills from the registry, and installs them as `.skills/` in the target project.

---

## Development Workflow

### Day-to-Day Cycle

```bash
# 1. Make code changes in dva-agentic-cli/

# 2. Run tests locally
cd dva-agentic-cli
make test                     # Unit tests
make test-cov                 # With coverage
make lint                     # Check code style

# 3. Re-install global CLI to pick up changes
cd ..
uv tool install --force ./dva-agentic-cli

# 4. Verify from any directory
cd /tmp && dva --version
```

### Running Tests

```bash
cd dva-agentic-cli

# All tests
make test

# With coverage report
make test-cov

# Specific test file
pytest tests/test_kg.py -v

# Specific test
pytest tests/test_kg.py::TestIngest::test_pdf -v

# Integration tests
make integration
```

### Code Quality

```bash
cd dva-agentic-cli

# Lint
make lint

# Auto-format
make format
```

### Local Dev Install (In-Project)

For working inside the `dva-agentic-cli` project itself (e.g., running tests):

```bash
cd dva-agentic-cli
uv venv
source .venv/bin/activate
make install-dev              # Editable install with dev deps

# Now 'dva' works in this venv AND tests can import the package
make test
```

> This local venv install is separate from the global `uv tool` install. Both can coexist.

### Vertex AI Authentication

```bash
# Configure Vertex AI (saves to ~/.dva-agentic/config.json)
dva init vertex-ai --project-id YOUR_PROJECT_ID

# Or authenticate manually
gcloud auth application-default login
```

---

## Common Operations

### Quick Reference

| Task | Command |
|------|---------|
| **CLI version** | `dva --version` |
| **CLI help** | `dva --help` |
| **Reinstall CLI globally** | `uv tool install --force ./dva-agentic-cli` |
| **List uv tools** | `uv tool list` |
| **Start MCP servers** | `cd dva-mcp-servers && docker compose up -d` |
| **Stop MCP servers** | `cd dva-mcp-servers && docker compose down` |
| **MCP server logs** | `cd dva-mcp-servers && docker compose logs -f` |
| **Start Neo4j** | `cd dva-kg-infrastructure/neo4j && docker compose up -d` |
| **Start LightRAG** | `cd dva-kg-infrastructure/lightrag && ./setup.sh` |
| **Check KG status** | `dva kg check` |
| **KG stats** | `dva kg stats` |
| **Run tests** | `cd dva-agentic-cli && make test` |
| **Lint code** | `cd dva-agentic-cli && make lint` |
| **Format code** | `cd dva-agentic-cli && make format` |
| **Onboard a project** | `dva code onboard --path /path/to/project` |
| **List data sources** | `dva data list` |
| **List MCP servers** | `dva mcp list` |

### Full Environment Startup

Start everything needed for a full local development session:

```bash
# 1. Start Docker services
cd dva-mcp-servers && docker compose up -d && cd ..
cd dva-kg-infrastructure/neo4j && docker compose up -d && cd ../..

# 2. Verify CLI
dva --version
dva kg check

# 3. Verify MCP
docker compose -f dva-mcp-servers/docker-compose.yml ps
```

### Full Environment Shutdown

```bash
docker compose -f dva-mcp-servers/docker-compose.yml down
docker compose -f dva-kg-infrastructure/neo4j/docker-compose.yml down
```

### Git Workflow

All repos use the `develop` branch:

```bash
cd dva-agentic-cli
git checkout develop
git pull origin develop

# Make changes, test, commit
make test && make lint
git add -A && git commit -m "feat: description"
git push origin develop
```

---

## Troubleshooting

### `dva` command not found

```bash
# Check if ~/.local/bin is on PATH
echo $PATH | tr ':' '\n' | grep local

# If missing, add to ~/.zshrc:
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Reinstall
uv tool install --force ./dva-agentic-cli
```

### `dva` shows old version after code changes

The global install is a snapshot, not editable. Reinstall:

```bash
uv tool install --force ./dva-agentic-cli
```

Or switch to editable mode:

```bash
uv tool install --editable ./dva-agentic-cli
```

### Docker network errors

```bash
# Create the shared network if missing
docker network create dva-network

# Verify
docker network ls | grep dva
```

### MCP server won't start

```bash
# Check if port is already in use
lsof -i :8126

# Check container logs
docker compose -f dva-mcp-servers/docker-compose.yml logs bitbucket-mcp

# Rebuild from scratch
docker compose -f dva-mcp-servers/docker-compose.yml build --no-cache bitbucket-mcp
docker compose -f dva-mcp-servers/docker-compose.yml up -d bitbucket-mcp
```

### Neo4j connection refused

```bash
# Check container
docker ps | grep neo4j

# Check logs
docker logs dva-neo4j

# Test connection
dva kg check
```

### Import errors when running `dva` commands

If optional commands fail (e.g., `dva kg`), install the optional dependency group:

```bash
uv tool install --force ./dva-agentic-cli --with "dva-agentic-cli[kg]"
```

### Conflicting `dva` installs

If you previously installed via `pip install -e .`, remove it:

```bash
pip uninstall dva-agentic-cli -y
```

Then verify only the uv tool version remains:

```bash
which -a dva
# Should show only: ~/.local/bin/dva
```

---

## Configuration Files

| File | Purpose |
|------|---------|
| `~/.dva-agentic/config.json` | CLI config (Vertex AI, data sources) |
| `~/.dva-agentic/kg-config.json` | Knowledge graph provider config |
| `~/.dva-agentic/mcp/registry.json` | MCP server registry |
| `dva-mcp-servers/.env` | MCP Docker environment (tokens, URLs) |
| `.windsurf/mcp_config.json` | Windsurf MCP server connections |

---

## Port Map

| Port | Service | Protocol |
|------|---------|----------|
| 7474 | Neo4j Browser | HTTP |
| 7687 | Neo4j Bolt | Bolt |
| 8001 | LightRAG API | HTTP |
| 8125 | KG MCP | HTTP |
| 8126 | Bitbucket MCP | SSE |
| 8127 | Glean MCP | SSE |
| 8128 | Jira MCP | SSE |
| 9090 | MCP Gateway | SSE |
| 9091 | MCP Proxy | SSE |
