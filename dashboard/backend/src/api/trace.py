"""Context trace API routes — what an agent actually read, per session."""

from fastapi import APIRouter, HTTPException, Query

from src.services import trace_service as svc
from src.services.trace_service import (
    SessionLedger,
    SessionRef,
    get_ledger,
    list_sessions,
)

router = APIRouter(prefix="/api/trace", tags=["trace"])


@router.get("/sessions", response_model=list[SessionRef])
async def api_list_sessions(limit: int = Query(25, ge=1, le=200)):
    """Recent sessions that read context, newest first."""
    try:
        return list_sessions(limit=limit)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}", response_model=SessionLedger)
async def api_get_ledger(session_id: str, limit: int = Query(500, ge=1, le=2000)):
    """One session's context ledger, oldest read first, with its budget rollup.

    An unknown session returns an empty ledger rather than a 404: a session
    that read nothing is a real and meaningful answer, and the caller renders
    the same empty state either way.
    """
    try:
        return get_ledger(session_id, limit=limit)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Context Playground — run a task, toggle a source off, watch the scores move.
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/playground/sources",
            response_model=list[svc.PlaygroundSource])
async def api_playground_sources(session_id: str):
    """Context slices this session's replay can switch off."""
    return svc.playground_sources(session_id)


@router.post("/sessions/{session_id}/playground",
             response_model=svc.PlaygroundComparison)
async def api_playground_run(session_id: str, body: svc.PlaygroundRequest):
    """Replay the session's question with context removed, and score the result."""
    return svc.playground_run(session_id, body)
