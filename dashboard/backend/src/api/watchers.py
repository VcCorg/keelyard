"""Watchers API — CRUD + trigger catalog + test-run.

Reads are open (every user needs to see what's wired to their agents);
writes will gain admin/lead gating once role-scoped tenancy for watchers
lands — for Phase 1 we intentionally keep the surface simple.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.services.watchers_service import (
    TestRunResult,
    TriggerModel,
    WatcherModel,
    WatcherView,
    delete_watcher,
    get_watcher,
    list_triggers,
    list_watchers,
    set_enabled,
    test_run,
    upsert_watcher,
    watchers_for_agent,
)

router = APIRouter(prefix="/api/watchers", tags=["watchers"])


@router.get("", response_model=list[WatcherView])
async def api_list_watchers():
    """Every watcher (spec + last-known state) — powers the /watchers list."""
    return list_watchers()


@router.get("/triggers", response_model=list[TriggerModel])
async def api_list_triggers():
    """Available triggers + their filter schemas — drives the create/edit form."""
    return list_triggers()


@router.get("/for-agent/{agent}", response_model=list[WatcherView])
async def api_watchers_for_agent(agent: str):
    """Watchers whose handler fires this agent (Agent Builder Triggers section)."""
    return watchers_for_agent(agent)


@router.get("/{name}", response_model=WatcherView)
async def api_get_watcher(name: str):
    view = get_watcher(name)
    if view is None:
        raise HTTPException(status_code=404, detail=f"watcher '{name}' not found")
    return view


@router.put("/{name}", response_model=WatcherView)
async def api_upsert_watcher(name: str, model: WatcherModel):
    if name != model.name:
        raise HTTPException(status_code=400, detail="URL name must match body.name")
    try:
        return upsert_watcher(model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("", response_model=WatcherView)
async def api_create_watcher(model: WatcherModel):
    try:
        return upsert_watcher(model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{name}")
async def api_delete_watcher(name: str):
    removed = delete_watcher(name)
    if not removed:
        raise HTTPException(status_code=404, detail=f"watcher '{name}' not found")
    return {"deleted": name}


@router.post("/{name}/pause", response_model=WatcherView)
async def api_pause_watcher(name: str):
    view = set_enabled(name, False)
    if view is None:
        raise HTTPException(status_code=404, detail=f"watcher '{name}' not found")
    return view


@router.post("/{name}/resume", response_model=WatcherView)
async def api_resume_watcher(name: str):
    view = set_enabled(name, True)
    if view is None:
        raise HTTPException(status_code=404, detail=f"watcher '{name}' not found")
    return view


@router.post("/{name}/test-run", response_model=TestRunResult)
async def api_test_run(name: str):
    """Poll the watcher once and return matches WITHOUT dispatching.

    The dashboard "Test run" button uses this to validate a filter before
    the user commits it live.
    """
    return await test_run(name)
