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
    kind: str = "cloud"          # cloud | local
    description: str = ""
    detail: str = ""


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
                        description=i.description, detail=i.detail)
        for i in cli_list_engines()
    ]


def preview_portable_context(req: PortableContextRequest) -> PortableContextResult:
    """Render a task's portable context bundle (preview — no files written).

    Routes through the neutral seam with the ``local`` engine in dry-run so the
    launch is audited (``source="dashboard"``) exactly like a Devin launch, then
    returns the full CONTEXT.md for preview/download. The CLI's ``dva context
    build`` writes the bundle to disk when you want the files.
    """
    from agentic_cli.execution import ExecutionSpec, create_session

    tags = ["dva"] + ([req.domain] if req.domain else []) + ([req.jira] if req.jira else []) + list(req.tags)
    spec = ExecutionSpec(
        prompt=req.prompt,
        title=req.title or (f"{req.jira}: {req.prompt}" if req.jira else req.prompt)[:120],
        jira=req.jira,
        domain=req.domain or "",
        tags=sorted(set(tags)),
        context=list(req.refs),
        dry_run=True,
    )
    res = create_session(spec, engine="local", source="dashboard")
    raw = res.raw or {}
    return PortableContextResult(
        engine=res.engine,
        bundle_id=res.session_id,
        context_md=raw.get("context_md", ""),
        item_count=int(raw.get("item_count", 0)),
        resolved=int(raw.get("resolved", 0)),
    )
