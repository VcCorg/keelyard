"""KG Context API endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from src.services.kg_service import (
    get_all_products_kg_summary,
    get_domain_links,
    get_domain_gaps,
    get_node_neighborhood,
    ProductKGSummary,
    KGLinkRow,
    KGGapRow,
    KGNeighborhood,
)
from src.services import kg_ingest_service as ingest_svc

router = APIRouter(prefix="/api/kg", tags=["kg"])


# ── Ingestion: reads ────────────────────────────────────────────────────────

@router.get("/ingest/jobs", response_model=list[ingest_svc.IngestJobInfo])
async def list_ingest_jobs(
    status: Optional[str] = Query(None),
    limit: int = Query(default=50, le=200),
):
    """List ingestion jobs (sync + async) from the CLI job queue."""
    try:
        return ingest_svc.list_ingest_jobs(status=status, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ingest/jobs/{job_id}", response_model=ingest_svc.IngestJobInfo)
async def get_ingest_job(job_id: str):
    job = ingest_svc.get_ingest_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job


@router.get("/ingest/domains", response_model=list[ingest_svc.IngestableDomain])
async def list_ingestable_domains():
    """List domains (with tracked-doc counts) that can have their KG built."""
    try:
        return ingest_svc.list_ingestable_domains()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Ingestion: streaming submit (SSE) ───────────────────────────────────────

def _sse(args: list[str]) -> EventSourceResponse:
    async def gen():
        async for line in ingest_svc.stream_kg_command(args):
            if line.startswith("__EXIT__"):
                yield {"event": "done", "data": line.split(" ", 1)[1].strip()}
            else:
                yield {"event": "log", "data": line}

    return EventSourceResponse(gen())


@router.get("/ingest/submit/stream")
async def ingest_submit_stream(
    domain: Optional[str] = Query(None, description="Domain slug to build KG for"),
    path: Optional[str] = Query(None, description="Direct path/URL to ingest"),
    source: Optional[str] = Query(None, description="Configured data source name"),
    format: Optional[str] = Query(None, description="Source format override"),
    provider: Optional[str] = Query(None, description="Target provider override"),
    workspace: Optional[str] = Query(None),
    depth: int = Query(3, le=10),
    top: Optional[int] = Query(None, description="Limit to first N pages (testing)"),
):
    """Run `dva kg ingest submit ...` (sync) and stream its output over SSE."""
    if not (domain or path or source):
        raise HTTPException(
            status_code=400,
            detail="Must provide one of: domain, path, or source.",
        )

    args = ["ingest", "submit"]
    if domain:
        args += ["--domain", domain, "--depth", str(depth)]
        if top:
            args += ["--top", str(top)]
    if path:
        args += ["--path", path]
    if source:
        args += ["--source", source]
    if format:
        args += ["--format", format]
    if provider:
        args += ["--provider", provider]
    if workspace:
        args += ["--workspace", workspace]
    return _sse(args)


@router.get("/products")
async def list_products():
    """Return all products with per-domain KG coverage stats."""
    try:
        result = get_all_products_kg_summary()
        print(f"DEBUG: get_all_products_kg_summary returned {len(result)} items")
        # Convert to dict for JSON serialization
        dumped = [item.model_dump() for item in result]
        print(f"DEBUG: Dumped {len(dumped)} items")
        return dumped
    except Exception as e:
        # Log error and return empty list instead of crashing
        print(f"Error getting KG products: {e}")
        import traceback
        traceback.print_exc()
        return []


@router.get("/{domain}/links", response_model=list[KGLinkRow])
async def domain_links(
    domain: str,
    limit: int = Query(default=200, le=500),
):
    """Return code→requirement edges for a domain, ordered by confidence."""
    return get_domain_links(domain, limit=limit)


@router.get("/{domain}/gaps", response_model=list[KGGapRow])
async def domain_gaps(domain: str):
    """Return requirement docs with no linked code entities (coverage gaps)."""
    return get_domain_gaps(domain)


@router.get("/{domain}/graph/{node_id:path}", response_model=KGNeighborhood)
async def node_graph(domain: str, node_id: str):
    """Return 1-hop graph neighborhood for a KG node (for the drilldown panel)."""
    result = get_node_neighborhood(node_id, domain)
    if not result.nodes:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found in domain '{domain}'")
    return result
