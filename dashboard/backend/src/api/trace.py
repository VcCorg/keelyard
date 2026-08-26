"""Context trace API routes — what an agent actually read, per session."""

from fastapi import APIRouter, HTTPException, Query

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
