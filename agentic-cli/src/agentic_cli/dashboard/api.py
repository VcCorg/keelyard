"""FastAPI backend for the DVA Agentic Dashboard."""

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from agentic_cli import tracker
from agentic_cli.templates.enums import UseCase, Framework, Tool
from agentic_cli.templates.config import USE_CASE_TOOLS

app = FastAPI(title="DVA Agentic Dashboard", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

@app.get("/api/products")
def list_products():
    return tracker.get_products()


@app.get("/api/products/{name}")
def get_product(name: str):
    p = tracker.get_product(name)
    if not p:
        raise HTTPException(404, f"Product '{name}' not found")
    return p


# ---------------------------------------------------------------------------
# Domains
# ---------------------------------------------------------------------------

@app.get("/api/domains")
def list_domains(product: Optional[str] = None):
    return tracker.get_domains(product=product)


@app.get("/api/domains/{name}")
def get_domain(name: str):
    d = tracker.get_domain(name)
    if not d:
        raise HTTPException(404, f"Domain '{name}' not found")
    d["repos"] = tracker.get_domain_repos(name)
    d["docs"] = tracker.get_domain_docs(name)
    return d


# ---------------------------------------------------------------------------
# Repos
# ---------------------------------------------------------------------------

@app.get("/api/repos")
def list_repos():
    return tracker.get_repos()


# ---------------------------------------------------------------------------
# Projects (created agent projects)
# ---------------------------------------------------------------------------

@app.get("/api/projects")
def list_projects():
    projects = tracker.get_projects()
    # Enrich with validation info
    for p in projects:
        p["validation"] = _validate_project(p)
    return projects


def _validate_project(project: dict) -> dict:
    """Validate a project's files and configuration."""
    path = Path(project.get("path", ""))
    checks = {
        "path_exists": path.exists(),
        "has_src": (path / "src").exists(),
        "has_pyproject": (path / "pyproject.toml").exists(),
        "has_env": (path / ".env").exists(),
        "has_domain_context": (path / ".domain-context.json").exists(),
        "has_persona_skills": (path / ".skills" / "domain").exists(),
    }

    use_case = project.get("use_case", "")
    if use_case == "scrum-master":
        checks["has_mcp_clients"] = (path / "src" / "mcp_clients.py").exists()
        checks["has_sprint_manager"] = (path / "src" / "sprint_manager.py").exists()
        checks["has_standup_generator"] = (path / "src" / "standup_generator.py").exists()
        checks["has_domain_loader"] = (path / "src" / "domain_loader.py").exists()
    elif use_case == "pr-reviewer":
        checks["has_mcp_client"] = (path / "src" / "mcp_client.py").exists()
        checks["has_watcher"] = (path / "src" / "watcher.py").exists()
        checks["has_reviewer"] = (path / "src" / "reviewer.py").exists()

    checks["score"] = sum(1 for v in checks.values() if v is True)
    checks["total"] = sum(1 for v in checks.values() if isinstance(v, bool))
    return checks


# ---------------------------------------------------------------------------
# Activity log
# ---------------------------------------------------------------------------

@app.get("/api/activity")
def list_activity(command: Optional[str] = None, limit: int = 50):
    return tracker.get_activity(command=command, limit=limit)


@app.get("/api/activity/summary")
def activity_summary():
    return tracker.get_activity_summary()


# ---------------------------------------------------------------------------
# Use cases & templates catalogue
# ---------------------------------------------------------------------------

@app.get("/api/catalogue/use-cases")
def list_use_cases():
    return [
        {
            "value": uc.value,
            "display_name": uc.display_name,
            "description": uc.description,
            "tools": [t.value for t in USE_CASE_TOOLS.get(uc, [])],
        }
        for uc in UseCase
    ]


@app.get("/api/catalogue/frameworks")
def list_frameworks():
    return [{"value": f.value, "display_name": f.display_name} for f in Framework]


@app.get("/api/catalogue/tools")
def list_tools():
    return [{"value": t.value, "display_name": t.display_name} for t in Tool]


# ---------------------------------------------------------------------------
# MCP health checks
# ---------------------------------------------------------------------------

@app.get("/api/mcp/health")
async def mcp_health():
    """Check connectivity to known MCP servers."""
    import httpx

    servers = {
        "bitbucket": os.getenv("MCP_BITBUCKET_URL", "http://localhost:8126/sse"),
        "jira": os.getenv("MCP_JIRA_URL", "http://localhost:8128/sse"),
        "confluence": os.getenv("MCP_CONFLUENCE_URL", "http://localhost:8129/sse"),
        "gateway": os.getenv("MCP_GATEWAY_URL", "http://localhost:9090/sse"),
        "kg": os.getenv("MCP_KG_URL", "http://localhost:8131/sse"),
        "memory": os.getenv("MCP_MEMORY_URL", "http://localhost:8130/sse"),
    }

    results = {}
    async with httpx.AsyncClient(timeout=3.0) as client:
        for name, url in servers.items():
            try:
                # SSE endpoints return text/event-stream on GET
                resp = await client.get(url, follow_redirects=True)
                results[name] = {
                    "url": url,
                    "status": "up" if resp.status_code < 500 else "error",
                    "status_code": resp.status_code,
                }
            except Exception:
                results[name] = {"url": url, "status": "down", "status_code": None}
    return results


# ---------------------------------------------------------------------------
# Persona skills
# ---------------------------------------------------------------------------

@app.get("/api/domains/{name}/skills")
def get_domain_skills(name: str):
    """List generated persona skill files for a domain."""
    d = tracker.get_domain(name)
    if not d:
        raise HTTPException(404, f"Domain '{name}' not found")

    # Same path logic as domain.py gen-skills: parents[4] from commands/ = agentic-project/
    skills_base = Path(__file__).resolve().parents[4] / "skills" / "domains" / name
    skills = {}
    for role_file in ["DOMAIN.md", "DEV.md", "QA.md", "SM.md", "BA.md"]:
        fp = skills_base / role_file
        if fp.exists():
            skills[role_file] = {
                "exists": True,
                "size": fp.stat().st_size,
                "preview": fp.read_text()[:500],
            }
        else:
            skills[role_file] = {"exists": False, "size": 0, "preview": ""}
    return skills


# ---------------------------------------------------------------------------
# Full context export
# ---------------------------------------------------------------------------

@app.get("/api/context")
def full_context():
    return tracker.get_full_context()


# ---------------------------------------------------------------------------
# Serve frontend
# ---------------------------------------------------------------------------

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", response_class=HTMLResponse)
def serve_index():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return index.read_text()
    return "<h1>DVA Dashboard</h1><p>Static files not found.</p>"
