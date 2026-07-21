"""Execution service — thin lens over the CLI's vendor-neutral execution seam.

The dashboard does not know engines directly; it delegates to
``agentic_cli.execution``. This exposes the registered engines and lets the UI
project a task's canonical context into a **portable, engine-neutral bundle**
(the ``local`` engine) — the same context Devin would receive, with no vendor.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class EngineInfoModel(BaseModel):
    name: str
    available: bool
    kind: str = "cloud"          # cloud | local | ide
    description: str = ""
    detail: str = ""
    supports_ask: bool = False


class SessionLaunchRequest(BaseModel):
    prompt: str
    title: str = ""
    jira: str = ""
    domain: Optional[str] = None
    tags: list[str] = []
    refs: list[str] = []
    engine: Optional[str] = None   # None → the org default (admin code_assist)
    dry_run: bool = True           # safe default; caller opts into a real launch


class SessionLaunchResult(BaseModel):
    engine: str
    session_id: Optional[str] = None
    url: Optional[str] = None
    status: Optional[str] = None
    is_new: bool = True
    dry_run: bool = False
    detail: dict = {}              # engine raw (handoff instructions, bundle path, …)


class AskRequest(BaseModel):
    prompt: str
    domain: Optional[str] = None
    refs: list[str] = []
    engine: Optional[str] = None   # None → the org default


class AskResultModel(BaseModel):
    engine: str
    answer: str = ""
    authoritative: bool = True
    session_id: Optional[str] = None
    url: Optional[str] = None


def default_engine() -> str:
    """The org's default code-assist engine (admin setting)."""
    try:
        from agentic_cli.admin import load_settings

        return load_settings().code_assist.default or "local"
    except Exception:  # noqa: BLE001
        return "local"


def enabled_engines() -> list[str]:
    try:
        from agentic_cli.admin import load_settings

        return list(load_settings().code_assist.enabled)
    except Exception:  # noqa: BLE001
        return ["devin", "local"]


class PortableContextRequest(BaseModel):
    prompt: str
    title: str = ""
    jira: str = ""
    domain: Optional[str] = None
    tags: list[str] = []
    refs: list[str] = []         # canonical context refs (okf://…)


class PortableContextResult(BaseModel):
    engine: str = "local"
    bundle_id: Optional[str] = None
    context_md: str = ""
    item_count: int = 0
    resolved: int = 0


def list_engines() -> list[EngineInfoModel]:
    """Registered execution engines and their availability (CLI is the source)."""
    from agentic_cli.execution import list_engines as cli_list_engines

    return [
        EngineInfoModel(name=i.name, available=i.available, kind=i.kind,
                        description=i.description, detail=i.detail,
                        supports_ask=getattr(i, "supports_ask", False))
        for i in cli_list_engines()
    ]


def launch_session(req: SessionLaunchRequest, actor: str | None = None) -> SessionLaunchResult:
    """Launch a build session on the selected (or org-default) engine.

    Vendor-neutral: routes through the same governed seam as every engine, so
    build governance + audit apply identically. Raises GovernanceViolation
    (→ 403 at the route) when a domain-less session is refused under 'enforce'.
    """
    from agentic_cli.execution import ExecutionSpec, create_session

    engine = req.engine or default_engine()
    tags = ["keel"] + ([req.domain] if req.domain else []) + list(req.tags)
    spec = ExecutionSpec(
        prompt=req.prompt,
        title=req.title or (f"{req.jira}: {req.prompt}" if req.jira else req.prompt)[:120],
        jira=req.jira, domain=req.domain or "", tags=sorted(set(tags)),
        context=list(req.refs), dry_run=req.dry_run,
    )
    res = create_session(spec, engine=engine, source="dashboard", actor=actor)
    return SessionLaunchResult(
        engine=res.engine, session_id=res.session_id, url=res.url, status=res.status,
        is_new=res.is_new, dry_run=res.dry_run, detail=res.raw or {})


def ask_engine(req: AskRequest, actor: str | None = None) -> AskResultModel:
    """Ask the selected (or org-default) engine about the codebase/domain."""
    from agentic_cli.execution import ExecutionSpec, ask

    engine = req.engine or default_engine()
    spec = ExecutionSpec(prompt=req.prompt, domain=req.domain or "", context=list(req.refs))
    res = ask(spec, engine=engine, source="dashboard", actor=actor)
    return AskResultModel(
        engine=res.engine, answer=res.answer, authoritative=res.authoritative,
        session_id=res.session_id, url=res.url)


def preview_portable_context(req: PortableContextRequest, actor: str | None = None) -> PortableContextResult:
    """Render a task's portable context bundle (preview — no files written).

    Routes through the neutral seam with the ``local`` engine in dry-run so the
    launch is audited (``source="dashboard"``) exactly like a Devin launch, then
    returns the full CONTEXT.md for preview/download. The CLI's ``keel context
    build`` writes the bundle to disk when you want the files.
    """
    from agentic_cli.execution import ExecutionSpec, create_session

    tags = ["keel"] + ([req.domain] if req.domain else []) + ([req.jira] if req.jira else []) + list(req.tags)
    spec = ExecutionSpec(
        prompt=req.prompt,
        title=req.title or (f"{req.jira}: {req.prompt}" if req.jira else req.prompt)[:120],
        jira=req.jira,
        domain=req.domain or "",
        tags=sorted(set(tags)),
        context=list(req.refs),
        dry_run=True,
    )
    res = create_session(spec, engine="local", source="dashboard", actor=actor)
    raw = res.raw or {}
    return PortableContextResult(
        engine=res.engine,
        bundle_id=res.session_id,
        context_md=raw.get("context_md", ""),
        item_count=int(raw.get("item_count", 0)),
        resolved=int(raw.get("resolved", 0)),
    )
