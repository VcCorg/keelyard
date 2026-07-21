"""Persona-tiered workspace API.

Lets the dashboard reflect the `keel workspace` / `keel domain sync` model:
list workspaces, resolve the folder a persona should open, stream worktree /
domain-sync creation, and launch a local editor at the resolved folder.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from src.services import workspace_service as svc

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


def _sse(gen) -> EventSourceResponse:
    """Wrap a line generator into named SSE `log`/`done` events."""
    async def event_gen():
        async for line in gen:
            if line.startswith("__EXIT__"):
                yield {"event": "done", "data": line.split(" ", 1)[1].strip()}
            else:
                yield {"event": "log", "data": line}

    return EventSourceResponse(event_gen())


class OpenIdeRequest(BaseModel):
    path: str
    editor: Optional[str] = None


@router.get("", response_model=list[svc.WorkspaceInfo])
async def api_list_workspaces(tier: Optional[str] = Query(None)):
    """List tracked persona workspaces (optionally filtered by tier)."""
    try:
        return svc.list_workspaces(tier=tier)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/editors")
async def api_list_editors():
    """Editor tools offered for 'Open in IDE' — the admin-enabled code-assist
    tools that are also installed (org default first)."""
    return {"editors": svc.enabled_editors()}


@router.get("/target", response_model=svc.WorkspaceTarget)
async def api_resolve_target(
    persona: str = Query(..., description="dev | tech-lead | solutions-architect"),
    product: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    repo: Optional[str] = Query(None),
):
    """Resolve the folder a persona should open + whether an action is needed."""
    try:
        return svc.resolve_target(persona, product=product, domain=domain, repo=repo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/open-ide", response_model=svc.OpenIdeResult)
async def api_open_ide(req: OpenIdeRequest):
    """Launch a local editor (windsurf/code/cursor) at the given folder."""
    try:
        return svc.open_in_ide(req.path, editor=req.editor)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/stream")
async def api_sync_stream(
    domain: str = Query(..., description="Domain slug"),
    persona: str = Query("tech-lead"),
    graphify: bool = Query(True),
    editor: Optional[str] = Query(None, description="Target editor (devin/windsurf/cursor/code) — sets skill placement"),
):
    """Stream `keel domain sync` — assembles the tech-lead (domain-tier) workspace."""
    from src.services import okf_service
    if okf_service.domain_busy(domain):
        raise HTTPException(status_code=409, detail=f"Domain '{domain}' is busy (enrich/export/sync running).")
    tool = svc.tool_for_editor(editor)
    return _sse(svc.stream_sync_domain(domain, persona=persona, graphify=graphify, tool=tool))


@router.get("/open/stream")
async def api_open_stream(
    domain: str = Query(..., description="Domain slug"),
    repo: str = Query(..., description="Repo slug linked to the domain"),
    persona: str = Query("dev"),
    graphify: bool = Query(False),
    editor: Optional[str] = Query(None, description="Target editor (devin/windsurf/cursor/code) — sets skill placement"),
):
    """Stream `keel workspace open` — materializes the dev (repo-tier) worktree."""
    tool = svc.tool_for_editor(editor)
    return _sse(svc.stream_open_workspace(domain, repo, persona=persona, graphify=graphify, tool=tool))
