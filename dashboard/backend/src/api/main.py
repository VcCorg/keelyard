"""Agent Playground — FastAPI application."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.agents import router as agents_router
from src.api.mcp import router as mcp_router
from src.api.activity import router as activity_router

# Chat rides on the optional [chat] extra (google-adk). Without it the whole
# app must still boot — chat endpoints degrade to 503 instead of crashing the
# process at import time (which read as "can't initialize keel" in the
# packaged desktop app).
try:
    from src.api.chat import router as chat_router
except ImportError as _chat_err:  # pragma: no cover - depends on extras
    from fastapi import APIRouter, HTTPException

    chat_router = APIRouter(prefix="/api/chat", tags=["chat"])
    _chat_reason = str(_chat_err)

    @chat_router.api_route("/{path:path}", methods=["GET", "POST", "DELETE", "PUT"])
    async def _chat_unavailable(path: str):
        raise HTTPException(
            status_code=503,
            detail=f"Chat is unavailable: optional dependency missing ({_chat_reason}). "
                   "Install the backend's [chat] extra (google-adk) to enable it.",
        )
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
from src.api.ideate import router as ideate_router
from src.api.execution import router as execution_router
from src.api.auth import router as auth_router
from src.api.admin import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    # Load ~/.keel/.env (then project ./.env) so integration tokens configured
    # via the CLI / setup panel are visible to the backend without exporting
    # them into the environment. Real exported vars still take precedence.
    try:
        from agentic_cli.env import load_env
        load_env()
    except Exception:
        pass
    # Ensure tracker DB exists (creates schema if needed)
    try:
        from agentic_cli.tracker import _ensure_db
        _ensure_db()
    except ImportError:
        pass
    yield


app = FastAPI(
    title="Keel",
    description="Keel — agentic product development platform. Governed, vendor-neutral orchestration for agent-driven development.",
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
app.include_router(ideate_router)
app.include_router(execution_router)
app.include_router(auth_router)
app.include_router(admin_router)


@app.get("/api/health")
async def health():
    """Dashboard backend health check."""
    return {"status": "ok", "version": "0.1.0"}


def _mount_frontend(app: FastAPI) -> None:
    """Serve the built React SPA when packaged as a desktop app (opt-in).

    Enabled by ``KEEL_SERVE_FRONTEND=/path/to/dist`` (the Vite build output). The
    desktop launcher points the Electron window at ``http://127.0.0.1:<port>/`` and
    this serves ``index.html`` + assets, with an SPA fallback so client-side routes
    (``/kg``, ``/admin``, …) resolve to ``index.html`` instead of 404. API and
    docs paths are never shadowed — the catch-all only handles non-``/api`` GETs.
    In normal web dev the env is unset and this is a no-op (Vite proxies ``/api``).
    """
    dist = os.environ.get("KEEL_SERVE_FRONTEND")
    if not dist:
        return
    dist_dir = Path(dist).expanduser()
    index = dist_dir / "index.html"
    if not index.is_file():
        return

    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    from starlette.exceptions import HTTPException as StarletteHTTPException

    # Hashed build assets (JS/CSS/img) under /assets, served with long cache.
    assets_dir = dist_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/", include_in_schema=False)
    async def _index():
        return FileResponse(str(index))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa_fallback(full_path: str):
        # Never intercept API/docs/openapi — let them 404 as real API errors.
        if full_path.startswith(("api/", "docs", "redoc", "openapi.json")):
            raise StarletteHTTPException(status_code=404)
        # Serve a real file if it exists (favicon, manifest, …); else the SPA shell.
        candidate = dist_dir / full_path
        if candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(index))


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


# Mount the SPA LAST so its catch-all never shadows the API routes above
# (Starlette matches routes in registration order). No-op unless
# KEEL_SERVE_FRONTEND is set (i.e. only in the packaged desktop app).
_mount_frontend(app)
