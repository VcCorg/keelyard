"""KG Context API endpoints."""

from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Query
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
from src.services import okf_service

router = APIRouter(prefix="/api/kg", tags=["kg"])


# ── OKF bundles ──────────────────────────────────────────────────────────────

@router.get("/okf/bundles", response_model=list[okf_service.OKFBundleInfo])
async def list_okf_bundles():
    """List domains that have an OKF Markdown bundle."""
    try:
        return okf_service.list_okf_bundles()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/okf/bundles/{domain}", response_model=okf_service.OKFBundleDetail)
async def get_okf_bundle(
    domain: str,
    source: str = Query("export", description="'export' (generated) or 'authored'"),
):
    """Bundle detail: validation report, FREQ traceability, quarantine counts."""
    try:
        return okf_service.get_okf_bundle_detail(domain, source=source)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/okf/export/stream")
async def okf_export_stream(
    domain: str = Query(..., description="Domain slug to export from Neo4j"),
    product: Optional[str] = Query(None),
    mint_freqs: bool = Query(True, description="Mint FREQ concepts from CWOW-NNNNNN"),
):
    """Run `dva kg okf export --domain ...` (no reindex) and stream output over SSE."""
    if okf_service.domain_busy(domain):
        raise HTTPException(status_code=409, detail=f"OKF for '{domain}' is busy (enrich/export/sync running).")
    args = okf_service.okf_export_args(domain, product=product, mint_freqs=mint_freqs)
    return _sse(args)


@router.get("/okf/busy/{domain}")
async def okf_busy(domain: str):
    """Whether a per-domain OKF run (enrich/export/sync) is currently in progress."""
    return {"domain": domain, "busy": okf_service.domain_busy(domain)}


@router.get("/okf/enrich/stream")
async def okf_enrich_stream(
    domain: str = Query(..., description="Domain slug; resolves all repos/docs from registered data"),
    source: str = Query("both", description="code | confluence | both"),
    code_source: str = Query("auto", description="auto | graphify | analyze"),
    generate_graphs: bool = Query(True, description="Run `graphify update` on linked repos missing a graph"),
    no_confluence: bool = Query(False, description="Skip the Confluence enrichment pass"),
    model: Optional[str] = Query(None, description="Vertex AI model for the LLM enrichment pass"),
    dry_run: bool = Query(False, description="Preview planned concepts/pages without writing"),
):
    """Run `dva kg okf enrich --domain ...` (graphify structural + Confluence) over SSE.

    The default `code_source=auto` uses each repo's graphify graph (no LLM),
    generating any missing graph first. This is the multi-repo, team-facing path
    that keeps the domain OKF bundle built from the actual code structure.
    """
    if source not in ("code", "confluence", "both"):
        raise HTTPException(status_code=400, detail="source must be code, confluence, or both.")
    if code_source not in ("auto", "graphify", "analyze"):
        raise HTTPException(status_code=400, detail="code_source must be auto, graphify, or analyze.")
    if not dry_run and okf_service.domain_busy(domain):
        raise HTTPException(status_code=409, detail=f"OKF for '{domain}' is busy (enrich/export/sync running).")
    args = okf_service.okf_enrich_args(
        domain, source=source, code_source=code_source, generate_graphs=generate_graphs,
        no_confluence=no_confluence, model=model, dry_run=dry_run,
    )
    return _sse(args)


@router.get("/okf/devin/status")
async def okf_devin_status():
    """Whether the backend has a Devin API key (controls live-push availability)."""
    return {"api_key_present": okf_service.devin_api_key_present()}


@router.get("/okf/devin/push/stream")
async def okf_devin_push_stream(
    domain: str = Query(..., description="Domain slug whose bundle to push"),
    source: str = Query("export", description="'export' (generated) or 'authored'"),
    types: str = Query("FREQ,Requirement", description="Comma-separated concept types"),
    dry_run: bool = Query(True, description="Preview payloads without calling the Devin API"),
):
    """Run `dva kg okf push-devin ...` and stream output over SSE.

    The Devin API key is read from the backend env ($DEVIN_API_KEY) and is never
    accepted as a query parameter. A live push requires that key to be present.
    """
    if not dry_run and not okf_service.devin_api_key_present():
        raise HTTPException(
            status_code=400,
            detail="Live push requires DEVIN_API_KEY in the backend environment. "
                   "Use dry_run=true to preview payloads.",
        )
    args = okf_service.okf_push_devin_args(domain, source=source, types=types, dry_run=dry_run)
    return _sse(args)


@router.get("/okf/devin/knowledge", response_model=okf_service.DevinKnowledgeList)
async def okf_devin_knowledge():
    """List all Devin Knowledge entries + folders for management."""
    if not okf_service.devin_api_key_present():
        raise HTTPException(status_code=400, detail="DEVIN_API_KEY not set in the backend environment.")
    try:
        return okf_service.devin_list_knowledge()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Devin API error: {e}")


@router.delete("/okf/devin/knowledge/{note_id}")
async def okf_devin_delete(note_id: str):
    """Delete a single Devin Knowledge entry by id."""
    if not okf_service.devin_api_key_present():
        raise HTTPException(status_code=400, detail="DEVIN_API_KEY not set in the backend environment.")
    try:
        okf_service.devin_delete_knowledge(note_id)
        return {"deleted": note_id}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Devin API error: {e}")


@router.post("/okf/devin/knowledge/{note_id}/move")
async def okf_devin_move(note_id: str, folder_id: Optional[str] = Query(None)):
    """Move an entry to a folder (folder_id empty/omitted = root)."""
    if not okf_service.devin_api_key_present():
        raise HTTPException(status_code=400, detail="DEVIN_API_KEY not set in the backend environment.")
    try:
        okf_service.devin_move_knowledge(note_id, folder_id)
        return {"moved": note_id, "folder_id": folder_id}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Devin API error: {e}")


@router.put("/okf/devin/knowledge/{note_id}")
async def okf_devin_update(note_id: str, update: okf_service.DevinKnowledgeUpdate):
    """Partial update of an entry (trigger only, repo link, body, or all fields)."""
    if not okf_service.devin_api_key_present():
        raise HTTPException(status_code=400, detail="DEVIN_API_KEY not set in the backend environment.")
    try:
        okf_service.devin_update_knowledge(note_id, update)
        return {"updated": note_id}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Devin API error: {e}")


@router.post("/okf/devin/knowledge/bulk-delete")
async def okf_devin_bulk_delete(payload: dict = Body(...)):
    """Delete multiple entries. Body: ``{"ids": ["note-...", ...]}``."""
    if not okf_service.devin_api_key_present():
        raise HTTPException(status_code=400, detail="DEVIN_API_KEY not set in the backend environment.")
    ids = payload.get("ids") or []
    if not ids:
        raise HTTPException(status_code=400, detail="Provide a non-empty 'ids' list.")
    try:
        return okf_service.devin_bulk_delete(ids)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Devin API error: {e}")


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
    product: Optional[str] = Query(None, description="Product to tie the KG to (mandatory unless a domain is given)"),
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

    # A knowledge graph must be tied to a product. The domain (which carries a
    # product) satisfies this; otherwise a product must be supplied explicitly.
    if not domain and not (product and product.strip()):
        raise HTTPException(
            status_code=400,
            detail="A product is required to ingest into the knowledge graph (domain is optional).",
        )

    args = ["ingest", "submit"]
    if domain:
        args += ["--domain", domain, "--depth", str(depth)]
        if top:
            args += ["--top", str(top)]
    if product and product.strip():
        args += ["--product", product.strip()]
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
