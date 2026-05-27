"""KG Context API endpoints."""

from fastapi import APIRouter, HTTPException, Query
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

router = APIRouter(prefix="/api/kg", tags=["kg"])


@router.get("/products", response_model=list[ProductKGSummary])
async def list_products():
    """Return all products with per-domain KG coverage stats."""
    return get_all_products_kg_summary()


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
