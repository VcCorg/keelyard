"""Devin workflow API routes — Sessions + Knowledge."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from agentic_cli.auth import PERM_SESSION_CREATE
from src.services.auth_service import actor_of, require
from src.services.devin_service import (
    CreateSessionRequest,
    CreateSessionResponse,
    DevinStatus,
    SessionDetail,
    SessionInfo,
    SnapshotInfo,
    create_knowledge,
    create_session,
    get_session_detail,
    get_status,
    list_domain_snapshots,
    list_local_sessions,
    send_session_message,
    verify_domain_snapshot,
)

router = APIRouter(prefix="/api/devin", tags=["devin"])


class MessageRequest(BaseModel):
    message: str


class CreateKnowledgeRequest(BaseModel):
    name: str
    body: str
    trigger_description: str = ""
    parent_folder_id: str | None = None


@router.get("/status", response_model=DevinStatus)
async def api_status():
    """Devin configuration + whether an API key is available to the backend."""
    return get_status()


# ── Sessions ─────────────────────────────────────────────────────────────────

@router.get("/sessions", response_model=list[SessionInfo])
async def api_list_sessions():
    """Locally-tracked Devin sessions (created via this CLI/dashboard)."""
    return list_local_sessions()


@router.post("/sessions", response_model=CreateSessionResponse)
async def api_create_session(
    req: CreateSessionRequest,
    request: Request,
    _principal=Depends(require(PERM_SESSION_CREATE)),
):
    """Create (trigger) a Devin session. Requires the ``session:create`` permission."""
    try:
        return create_session(req, actor=actor_of(request))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def api_session_detail(session_id: str):
    """Live status + structured output for a session."""
    try:
        return get_session_detail(session_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/sessions/{session_id}/message")
async def api_session_message(session_id: str, req: MessageRequest):
    """Send a follow-up message to a running session."""
    try:
        return send_session_message(session_id, req.message)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc))


# ── Snapshots (per-domain registry + meta-repo drift) ───────────────────────

@router.get("/snapshots", response_model=list[SnapshotInfo])
async def api_list_snapshots():
    """Locally-registered per-domain Devin snapshots with drift status."""
    try:
        return list_domain_snapshots()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/snapshots/{domain}/verify", response_model=SnapshotInfo)
async def api_verify_snapshot(domain: str):
    """Re-verify a single domain's snapshot against its meta-repo."""
    try:
        return verify_domain_snapshot(domain)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc))


# ── Knowledge (reuses the existing OKF service) ──────────────────────────────

@router.get("/knowledge")
async def api_list_knowledge():
    """List all Devin Knowledge entries + folders (live API)."""
    from src.services.okf_service import devin_list_knowledge

    try:
        return devin_list_knowledge()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/knowledge")
async def api_create_knowledge(req: CreateKnowledgeRequest):
    """Create a Devin Knowledge entry (admin-gated in the UI)."""
    try:
        return create_knowledge(
            name=req.name,
            body=req.body,
            trigger_description=req.trigger_description,
            parent_folder_id=req.parent_folder_id,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/knowledge/{note_id}")
async def api_delete_knowledge(note_id: str):
    """Delete a Devin Knowledge entry."""
    from src.services.okf_service import devin_delete_knowledge

    try:
        devin_delete_knowledge(note_id)
        return {"deleted": note_id}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc))
