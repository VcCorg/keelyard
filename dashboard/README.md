# Agent Playground

Web dashboard for the Agentic Platform — manage agents, deploy applications, and interact via chat.

## Architecture

```
FastAPI Backend (Python)        React Frontend (TypeScript)
├── /api/agents/*               ├── Dashboard (overview)
├── /api/mcp/*                  ├── Agents (list, start/stop, logs)
├── /api/activity/*             ├── MCP Servers (health, manage)
├── /api/chat/* (Phase 6-7)     ├── Activity (timeline)
└── /api/overview               └── Chat (interactive agents, Phase 7)
```

## Quick Start

```bash
# Backend
cd backend
pip install -e ".[dev]"
uvicorn src.api.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Or use the Makefile:
```bash
make install
make backend   # Terminal 1
make frontend  # Terminal 2
```

### One command for every OS (macOS / Linux / Windows)

A single cross-platform launcher (`scripts/dashboard.py`) auto-detects the OS
and runs both services in the background — same invocation everywhere:

```bash
python scripts/dashboard.py start            # backend (:8000) + frontend (:5173)
python scripts/dashboard.py start --force-restart   # reclaim busy ports, no prompt
python scripts/dashboard.py start --backend  # backend only
python scripts/dashboard.py status
python scripts/dashboard.py stop
python scripts/dashboard.py restart
```

It logs to `dashboard/backend.log` / `dashboard/frontend.log`, records PIDs in
`dashboard/.backend.pid` / `.frontend.pid`, and **warns before killing** a
process that already owns a port (unless `--force-restart`, or a non-interactive
shell, which skips). Integration tokens are read from `~/.keel/.env`
(`%USERPROFILE%\.keel\.env`) automatically — no shell exports needed.

The bash installer can start it after install:

```bash
./install-agentic-cli.sh --start [--force-restart]
```

### Windows (PowerShell convenience wrappers)

If you prefer PowerShell verbs, thin wrappers at the repo root call the same
launcher (no Git Bash/WSL needed):

```powershell
./start-dashboard.ps1                 # start both
./start-dashboard.ps1 -ForceRestart   # reclaim busy ports
./start-backend.ps1                   # backend only
./start-frontend.ps1                  # frontend only
./start-dashboard.ps1 -Status
./start-dashboard.ps1 -Stop

# If scripts are blocked by execution policy:
#   pwsh -ExecutionPolicy Bypass -File .\start-dashboard.ps1
```

## Production (Docker)

A production stack is provided via `docker-compose.prod.yml`: the backend runs
FastAPI under uvicorn, and the frontend is built to static assets and served by
nginx, which also reverse-proxies `/api` (incl. SSE streams) to the backend.

```bash
# From the dashboard/ directory
docker compose -f docker-compose.prod.yml up -d --build
# Open http://localhost:8080
```

Configuration:

- **Backend env** — pass integration credentials via environment or an `.env`
  file in `dashboard/` (e.g. `BITBUCKET_SERVER_URL`, `JIRA_SERVER_URL`,
  `CONFLUENCE_SERVER_URL` and their `*_PERSONAL_ACCESS_TOKEN`s, `DEVIN_API_KEY`).
  All are optional for the UI itself.
- **Frontend API base** — baked at build time via the `VITE_API_BASE` build arg
  (default `/api`, proxied by nginx). Override in the compose file if needed.
- **MCP management** — the dashboard's MCP start/stop endpoints shell out to
  `docker`. To enable them in the container, uncomment the Docker socket mount
  in `docker-compose.prod.yml`.

> The backend image build context is the **repository root** (it installs the
> local `agentic-cli` package); the compose file sets this automatically.

## API Endpoints

### Agents
- `GET /api/agents` — List all tracked agents
- `GET /api/agents/{name}` — Agent detail
- `POST /api/agents/{name}/start` — Start agent daemon
- `POST /api/agents/{name}/stop` — Stop agent
- `GET /api/agents/{name}/logs` — SSE log stream
- `GET /api/agents/projects` — Discover agent projects

### MCP Servers
- `GET /api/mcp/servers` — List MCP servers with health
- `GET /api/mcp/servers/{name}` — Server detail
- `GET /api/mcp/health` — Health check all
- `POST /api/mcp/servers/{name}/start` — Start Docker service
- `POST /api/mcp/servers/{name}/stop` — Stop Docker service
- `GET /api/mcp/servers/{name}/logs` — SSE Docker log stream

### Activity
- `GET /api/activity` — Recent activity (filterable)
- `GET /api/activity/stats` — Aggregate stats

### Overview
- `GET /api/overview` — Dashboard summary
- `GET /api/health` — Backend health check

## Tech Stack

- **Backend:** FastAPI + uvicorn, imports agentic-cli as library
- **Frontend:** React + Vite + TailwindCSS + shadcn/ui
- **Real-time:** SSE for log streaming, REST polling for status
- **Chat (Phase 6-7):** WebSocket + Google ADK AgentRunner
