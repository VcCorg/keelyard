"""Admin API routes — app branding + navigation visibility.

GET is open (every user needs branding + their nav visibility to render the
app). PUT requires the ``admin:*`` permission and records the acting principal.
"""
from fastapi import APIRouter, Depends, HTTPException, Request

from agentic_cli.auth import PERM_ADMIN
from src.services.admin_service import (
    AdminSettingsModel,
    AdminSettingsUpdate,
    get_settings,
    update_settings,
)
from src.services.auth_service import actor_of, require

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/settings", response_model=AdminSettingsModel)
async def api_get_settings():
    """Current app branding + nav-visibility overrides (readable by all users)."""
    try:
        return get_settings()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings", response_model=AdminSettingsModel)
async def api_update_settings(
    update: AdminSettingsUpdate,
    request: Request,
    _principal=Depends(require(PERM_ADMIN)),
):
    """Update branding and/or nav visibility. Requires the ``admin:*`` permission."""
    try:
        return update_settings(update, actor=actor_of(request))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))
