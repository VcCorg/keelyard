"""Auth API routes — current identity + RBAC model for the UI."""

from fastapi import APIRouter, Request

from src.services.auth_service import MeResponse, me

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me", response_model=MeResponse)
async def get_me(request: Request):
    """The identity the configured provider resolves for this request (roles + permissions)."""
    return me(request)
