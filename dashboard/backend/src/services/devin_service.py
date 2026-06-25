"""Devin service — thin proxy over the reusable ``agentic_cli.devin`` package.

Wraps Sessions + Knowledge so the dashboard can drive Devin workflows. The API
key is never sent from the browser; the backend reads ``$DEVIN_API_KEY`` from
its own environment.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

# Repo root: .../dashboard/backend/src/services/devin_service.py -> parents[4]
REPO_ROOT = Path(__file__).resolve().parents[4]
EXPORT_DIR = REPO_ROOT / "knowledge-export"
DOMAINS_DIR = REPO_ROOT / "skills" / "domains"


# ── Transport models ─────────────────────────────────────────────────────────

class DevinStatus(BaseModel):
    api_key_present: bool = False
    base_url: str = ""
    default_max_acu: int = 10
    domains: dict[str, Any] = {}


class SessionInfo(BaseModel):
    session_id: str
    url: Optional[str] = None
    status: Optional[str] = None
    title: Optional[str] = None
    domain: Optional[str] = None
    jira: Optional[str] = None
    tags: list[str] = []
    created_at: Optional[str] = None


class CreateSessionRequest(BaseModel):
    prompt: str
    title: str = ""
    domain: Optional[str] = None
    jira: str = ""
    bundle: Optional[str] = None
    knowledge_from_sync: bool = False
    knowledge_ids: list[str] = []
    snapshot_id: Optional[str] = None
    playbook_id: Optional[str] = None
    tags: list[str] = []
    max_acu: Optional[int] = None
    idempotent: bool = False
    unlisted: bool = False
    dry_run: bool = False


class CreateSessionResponse(BaseModel):
    dry_run: bool = False
    session_id: Optional[str] = None
    url: Optional[str] = None
    status: Optional[str] = None
    is_new: bool = True
    reused_local: bool = False
    payload: dict[str, Any] = {}
    knowledge_count: int = 0


class SessionDetail(BaseModel):
    session_id: str
    url: Optional[str] = None
    status: Optional[str] = None
    structured_output: Any = None
    raw: dict[str, Any] = {}


# ── Config ───────────────────────────────────────────────────────────────────

def get_status() -> DevinStatus:
    from agentic_cli.devin.config import DevinConfig, has_api_key

    cfg = DevinConfig.load()
    return DevinStatus(
        api_key_present=has_api_key(),
        base_url=cfg.base_url,
        default_max_acu=cfg.default_max_acu,
        domains=cfg.domains(),
    )


# ── Bundle helpers (OKF grounding) ───────────────────────────────────────────

def _bundle_dir(domain: Optional[str], bundle: Optional[str]) -> Optional[Path]:
    if bundle:
        return Path(bundle)
    if domain:
        export = EXPORT_DIR / domain
        if (export / ".devin-sync.json").exists() or export.exists():
            return export
        authored = DOMAINS_DIR / domain / "knowledge"
        if authored.exists():
            return authored
    return None


def _knowledge_ids_from_sync(bundle_dir: Optional[Path]) -> list[str]:
    if not bundle_dir:
        return []
    from agentic_cli.kg.okf.devin import load_sync

    ids: list[str] = []
    for rec in load_sync(bundle_dir).values():
        kid = rec.get("id")
        if kid:
            ids.append(kid)
    return ids


# ── Sessions ─────────────────────────────────────────────────────────────────

def create_session(req: CreateSessionRequest) -> CreateSessionResponse:
    from agentic_cli.devin import SessionSpec, create_session as core_create
    from agentic_cli.devin.config import DevinConfig

    cfg = DevinConfig.load()
    dconf = cfg.domain(req.domain) if req.domain else {}

    kids = list(req.knowledge_ids)
    if req.knowledge_from_sync:
        kids += _knowledge_ids_from_sync(_bundle_dir(req.domain, req.bundle))

    tags = ["dva"] + ([req.domain] if req.domain else []) + ([req.jira] if req.jira else []) + list(req.tags)

    spec = SessionSpec(
        prompt=req.prompt,
        title=req.title or (f"{req.domain or 'devin'} · {req.jira}".strip(" ·")),
        snapshot_id=req.snapshot_id or dconf.get("snapshot_id"),
        playbook_id=req.playbook_id or dconf.get("playbook_id"),
        knowledge_ids=sorted(set(kids)),
        tags=sorted(set(tags)),
        idempotent=req.idempotent,
        max_acu_limit=req.max_acu if req.max_acu is not None else cfg.default_max_acu,
        unlisted=req.unlisted,
        domain=req.domain or "",
        jira=req.jira,
    )

    res = core_create(spec, dry_run=req.dry_run, base_url=cfg.base_url)
    return CreateSessionResponse(
        dry_run=res.dry_run,
        session_id=res.session_id,
        url=res.url,
        status=res.status,
        is_new=res.is_new,
        reused_local=res.reused_local,
        payload=res.payload,
        knowledge_count=len(spec.knowledge_ids),
    )


def list_local_sessions() -> list[SessionInfo]:
    from agentic_cli.devin import list_local

    out: list[SessionInfo] = []
    for r in list_local():
        out.append(SessionInfo(
            session_id=r.get("session_id", "?"),
            url=r.get("url"),
            status=r.get("last_status"),
            title=r.get("title"),
            domain=r.get("domain"),
            jira=r.get("jira"),
            tags=r.get("tags", []) or [],
            created_at=r.get("created_at"),
        ))
    return out


def get_session_detail(session_id: str) -> SessionDetail:
    from agentic_cli.devin import get_session

    res = get_session(session_id)
    return SessionDetail(
        session_id=session_id, url=res.url, status=res.status,
        structured_output=res.structured_output, raw=res.payload,
    )


def send_session_message(session_id: str, message: str) -> dict[str, Any]:
    from agentic_cli.devin import send_message

    return send_message(session_id, message)


# ── Knowledge ────────────────────────────────────────────────────────────────

def create_knowledge(name: str, body: str, trigger_description: str = "",
                     parent_folder_id: Optional[str] = None) -> dict[str, Any]:
    """Create a Devin Knowledge entry via the live API (admin-only in the UI)."""
    from agentic_cli.devin import get_client

    payload: dict[str, Any] = {
        "name": name,
        "body": body,
        "trigger_description": trigger_description or f"Use the '{name}' skill.",
    }
    if parent_folder_id:
        payload["parent_folder_id"] = parent_folder_id
    with get_client() as client:
        return client.create(payload)
