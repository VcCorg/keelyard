"""Integration status API — aggregated health of external dependencies."""

from fastapi import APIRouter

from src.services.integrations_service import IntegrationsResponse, get_integrations

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.get("/status", response_model=IntegrationsResponse)
async def api_integrations_status():
    """Snapshot of backend + auth + integration health for status icons."""
    return get_integrations()
