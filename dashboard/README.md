# Agentic Dashboard

Web dashboard for the Agentic Platform — manage agents, MCP servers, and interact via chat.

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
