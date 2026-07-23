"""KG ingest service — thin proxy over the agentic-cli core logic.

Design principle (mirrors domain_service.py):
- The dashboard NEVER re-implements ingestion logic.
- Reads (job list/status, ingestable domains) import the CLI's
  `agentic_cli.kg.async_ingest` manager and `agentic_cli.tracker` directly.
- The long-running ingest itself is executed by shelling out to the real
  `keel kg ingest submit ...` CLI and streaming its stdout, so all the
  Confluence/git/Neo4j/LightRAG logic lives in exactly one place.
"""

import asyncio
import json
import os
import shutil
import sys
from typing import Any, AsyncGenerator, Optional

from pydantic import BaseModel

from src.services.kg_ingest_progress import ProgressParser


# ── Pydantic models (transport shapes only — not logic) ─────────────────────

class IngestJobInfo(BaseModel):
    job_id: str
    source: str
    source_type: str = ""
    format: Optional[str] = None
    provider: str = ""
    status: str = ""
    is_async: bool = False
    workspace: Optional[str] = None
    domain: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    result: Optional[dict[str, Any]] = None


class IngestableDomain(BaseModel):
    slug: str
    product: str
    domain: str
    doc_count: int = 0
    repo_count: int = 0
    kg_ingested: int = 0
    confluence_space: Optional[str] = None
    confluence_url: Optional[str] = None


# ── CLI access helpers ──────────────────────────────────────────────────────

def _tracker():
    from agentic_cli import tracker
    return tracker


def _manager():
    from agentic_cli.kg.async_ingest import get_manager
    return get_manager()


def resolve_cli_command() -> list[str]:
    """Resolve how to invoke the keel CLI for subprocess streaming."""
    keel = shutil.which("keel")
    if keel:
        return [keel]
    return [sys.executable, "-m", "agentic_cli.main"]


def _iso(dt) -> Optional[str]:
    if dt is None:
        return None
    try:
        return dt.isoformat()
    except Exception:
        return str(dt)


# ── Reads (library import) ──────────────────────────────────────────────────

def _to_job_info(job) -> IngestJobInfo:
    md = getattr(job, "metadata", {}) or {}
    status = getattr(job, "status", "")
    status_val = getattr(status, "value", status)
    return IngestJobInfo(
        job_id=job.job_id,
        source=str(job.source),
        source_type=getattr(job, "source_type", "") or "",
        format=getattr(job, "format", None),
        provider=getattr(job, "provider", "") or "",
        status=str(status_val),
        is_async=bool(getattr(job, "is_async", False)),
        workspace=getattr(job, "workspace", None),
        domain=md.get("domain"),
        created_at=_iso(getattr(job, "created_at", None)),
        started_at=_iso(getattr(job, "started_at", None)),
        completed_at=_iso(getattr(job, "completed_at", None)),
        error=getattr(job, "error", None),
        result=getattr(job, "result", None),
    )


def list_ingest_jobs(status: Optional[str] = None, limit: int = 50) -> list[IngestJobInfo]:
    """List ingestion jobs (sync + async) from the CLI's job queue."""
    from agentic_cli.kg.async_ingest import JobStatus

    status_filter = None
    if status:
        try:
            status_filter = JobStatus(status.lower())
        except ValueError:
            raise ValueError(
                f"Invalid status '{status}'. Valid: pending, running, completed, failed, cancelled."
            )

    jobs = _manager().list_jobs(status=status_filter, limit=limit)
    return [_to_job_info(j) for j in jobs]


def get_ingest_job(job_id: str) -> Optional[IngestJobInfo]:
    job = _manager().get_job(job_id)
    return _to_job_info(job) if job else None


def list_ingestable_domains() -> list[IngestableDomain]:
    """List domains with tracked docs, so the UI can trigger a domain KG build."""
    t = _tracker()
    domains = t.get_domains() or []
    out: list[IngestableDomain] = []
    for d in domains:
        slug = d.get("name", "")
        docs = t.get_domain_docs(slug) or []
        repos = t.get_domain_repos(slug) or []
        out.append(IngestableDomain(
            slug=slug,
            product=d.get("product", ""),
            domain=d.get("domain", ""),
            doc_count=len(docs),
            repo_count=len(repos),
            kg_ingested=d.get("kg_ingested", 0) or 0,
            confluence_space=d.get("confluence_space"),
            confluence_url=d.get("confluence_url"),
        ))
    return out


# ── Long-running ingest (subprocess + streaming) ────────────────────────────

async def stream_kg_command(args: list[str]) -> AsyncGenerator[str, None]:
    """Run `keel kg <args>` and yield stdout/stderr lines as they arrive.

    Emits three kinds of frames the SSE layer decodes:
      * plain text  → forwarded as `log` events
      * `__PROGRESS__ {json}` → forwarded as `progress` events (phase, current,
        total, message, elapsed_ms) so the UI can render a progress bar
      * `__EXIT__ <code>` → terminal exit code
    """
    cmd = resolve_cli_command() + ["kg"] + args
    yield f"$ {' '.join(cmd)}"

    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
    )

    assert proc.stdout is not None
    parser = ProgressParser()
    while True:
        raw = await proc.stdout.readline()
        if not raw:
            break
        line = raw.decode(errors="replace").rstrip("\n")
        yield line
        event = parser.feed(line)
        if event is not None:
            yield "__PROGRESS__ " + json.dumps(event.to_dict())

    rc = await proc.wait()
    yield f"__EXIT__ {rc}"
