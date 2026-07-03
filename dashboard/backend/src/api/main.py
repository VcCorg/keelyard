"""Agent Playground — FastAPI application."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.agents import router as agents_router
from src.api.mcp import router as mcp_router
from src.api.activity import router as activity_router
from src.api.chat import router as chat_router
from src.api.terminal import router as terminal_router
from src.api.skills import router as skills_router
from src.api.deployments import router as deployments_router
from src.api.kg import router as kg_router
from src.api.domain import router as domain_router
from src.api.workspace import router as workspace_router
from src.api.data import router as data_router
from src.api.code import router as code_router
from src.api.eval import router as eval_router
from src.api.cli import router as cli_router
from src.api.runs import router as runs_router
from src.api.devin import router as devin_router
from src.api.integrations import router as integrations_router
from src.api.setup import router as setup_router
from src.api.jira import router as jira_router
from src.api.build import router as build_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    # Ensure tracker DB exists (creates schema if needed)
    try:
        from agentic_cli.tracker import _ensure_db
        _ensure_db()
    except ImportError:
        pass
    yield


app = FastAPI(
    title="Agent Playground",
    description="Web dashboard for Agentic Platform — manage agents, deploy applications, and interact via chat",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:5174",  # Vite dev server (fallback port)
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(agents_router)
app.include_router(mcp_router)
app.include_router(activity_router)
app.include_router(chat_router)
app.include_router(terminal_router)
app.include_router(skills_router)
app.include_router(deployments_router)
app.include_router(kg_router)
app.include_router(domain_router)
app.include_router(workspace_router)
app.include_router(data_router)
app.include_router(code_router)
app.include_router(eval_router)
app.include_router(cli_router)
app.include_router(runs_router)
app.include_router(devin_router)
app.include_router(integrations_router)
app.include_router(setup_router)
app.include_router(jira_router)
app.include_router(build_router)


@app.get("/api/health")
async def health():
    """Dashboard backend health check."""
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/overview")
async def overview():
    """Quick overview for the dashboard home page."""
    from src.services.agent_service import list_agents, discover_agent_projects, validate_project, get_project_domain
    from src.services.mcp_service import list_mcp_servers, check_health
    from src.services.activity_service import get_activity, get_activity_stats

    agents = list_agents()
    mcp_servers = list_mcp_servers()
    health_results = check_health()
    recent_activity = get_activity(limit=5)
    stats = get_activity_stats()

    healthy_count = sum(1 for h in health_results if h.healthy)

    # Enrich projects with validation
    projects = discover_agent_projects()
    for p in projects:
        p.validation = validate_project(p.path, p.use_case)
        p.domain = get_project_domain(p.path)
    valid_count = sum(1 for p in projects if p.validation and p.validation.score == p.validation.total)
    domain_count = len(set(p.domain for p in projects if p.domain))

    return {
        "agents": {
            "total": len(agents),
            "running": sum(1 for a in agents if a.status == "running"),
            "stopped": sum(1 for a in agents if a.status == "stopped"),
        },
        "mcp_servers": {
            "total": len(mcp_servers),
            "healthy": healthy_count,
            "unhealthy": len(health_results) - healthy_count,
        },
        "activity": {
            "total_commands": stats.total_commands,
            "total_errors": stats.total_errors,
            "last_activity": stats.last_activity,
            "recent": [entry.model_dump() for entry in recent_activity],
        },
        "projects": {
            "total": len(projects),
            "valid": valid_count,
            "with_domain": domain_count,
            "items": [p.model_dump() for p in projects],
        },
    }
