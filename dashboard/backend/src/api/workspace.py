"""Persona-tiered workspace API.

Lets the dashboard reflect the `keel workspace` / `keel domain sync` model:
list workspaces, resolve the folder a persona should open, stream worktree /
domain-sync creation, and launch a local editor at the resolved folder.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from src.services import template_service as tmpl
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
    tools that are also installed (org default first), plus the org default's
    editor key so the UI can flag it as missing when it isn't installed
    (rather than silently opening a different vendor).
    """
    return {
        "editors": svc.enabled_editors(),
        "default": svc._org_default_editor(),
    }


@router.get("/target", response_model=svc.WorkspaceTarget)
async def api_resolve_target(
    persona: str = Query(..., description="dev | tech-lead | solutions-architect"),
    product: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    repo: Optional[str] = Query(None),
    drift: bool = Query(False, description="Also classify template drift (slow: re-renders the template)"),
):
    """Resolve the folder a persona should open + whether an action is needed.

    ``drift`` is opt-in so the common case stays instant; the UI fetches it
    separately and lets the chip settle in afterwards.
    """
    import asyncio

    try:
        return await asyncio.to_thread(
            svc.resolve_target, persona, product, domain, repo, drift)
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


# ── Template & upstream (two-way flow with the shared template) ─────────────-

def _require_template_write():
    """Upgrading a repo, and especially promoting into the shared template,
    changes governed artifacts — the same lead permission skill promotion uses."""
    from agentic_cli.auth import PERM_KNOWLEDGE_PROJECT
    from src.services.auth_service import require

    return require(PERM_KNOWLEDGE_PROJECT)


@router.get("/template/status", response_model=tmpl.TemplateStatus)
async def api_template_status(
    domain: str = Query(..., description="Domain slug"),
    meta: Optional[str] = Query(None, description="Explicit meta-repo path (defaults to the workspace location)"),
):
    """Classify a domain meta-repo against the current template (read-only).

    Slow enough to run off the event loop: it re-renders the template into a
    temp dir to compare against.
    """
    import asyncio

    try:
        return await asyncio.to_thread(tmpl.template_status, domain, meta)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/template/overlay", response_model=tmpl.OverlayInfo)
async def api_template_overlay():
    """Files the shared template overlay currently provides (promoted content)."""
    try:
        return tmpl.overlay_info()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/template/promotable", response_model=tmpl.PromotableFiles)
async def api_template_promotable(domain: str = Query(..., description="Domain slug")):
    """Local files this domain could contribute back to the template."""
    import asyncio

    try:
        return await asyncio.to_thread(tmpl.promotable_files, domain)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/template/upgrade/stream")
async def api_template_upgrade_stream(
    domain: str = Query(..., description="Domain slug"),
    apply: bool = Query(False, description="Write the changes (otherwise preview only)"),
    prune: bool = Query(False, description="Also delete files the template no longer generates"),
    force: bool = Query(False, description="Overwrite files with uncommitted changes"),
    _principal=Depends(_require_template_write()),
):
    """Stream `keel domain template upgrade` — pull template updates down.

    Preview by default. Locally-modified and domain-authored files are never
    touched; both-sides conflicts are left in place with a `.new` sidecar.
    """
    return _sse(tmpl.stream_upgrade(domain, apply=apply, prune=prune, force=force))


@router.get("/template/promote/stream")
async def api_template_promote_stream(
    domain: str = Query(..., description="Domain slug"),
    file: list[str] = Query(..., description="Repo-relative file(s) to promote"),
    apply: bool = Query(False, description="Write into the overlay (otherwise preview only)"),
    push: bool = Query(False, description="Push the promotion branch to origin"),
    allow_unreviewed: bool = Query(False, description="Proceed despite residual domain-specific content"),
    _principal=Depends(_require_template_write()),
):
    """Stream `keel domain template promote` — push a local improvement up.

    Preview by default. The CLI re-tokenizes the file, verifies the template
    renders back to the original, and refuses content that still looks
    domain-specific unless ``allow_unreviewed``.
    """
    if not file:
        raise HTTPException(status_code=400, detail="At least one file is required")
    return _sse(tmpl.stream_promote(domain, file, apply=apply, push=push,
                                    allow_unreviewed=allow_unreviewed))


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
