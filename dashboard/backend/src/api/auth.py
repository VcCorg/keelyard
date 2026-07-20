"""Auth API routes — current identity + RBAC model for the UI."""

from fastapi import APIRouter, Query, Request

from src.services.auth_service import (
    MeResponse,
    PermissionCheck,
    RbacModel,
    check_permission,
    me,
    rbac_model,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me", response_model=MeResponse)
async def get_me(request: Request):
    """The identity the configured provider resolves for this request (roles + permissions)."""
    return me(request)


@router.get("/roles", response_model=RbacModel)
async def get_roles():
    """The RBAC model — roles, the permissions each grants, and personas.

    Read-only reference the Identity & Access page renders as a matrix; mirrors
    `keel auth roles`.
    """
    return rbac_model()


@router.get("/check", response_model=PermissionCheck)
async def get_check(
    request: Request,
    permission: str = Query(..., description="Permission slug, e.g. knowledge:project"),
):
    """Whether the current principal has ``permission`` (mirrors `keel auth check`)."""
    return check_permission(request, permission)
