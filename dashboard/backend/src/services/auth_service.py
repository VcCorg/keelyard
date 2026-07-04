"""Auth service — resolves the request principal and enforces RBAC.

Identity and the role model live in ``agentic_cli.auth`` (the CLI is the source
of truth). The dashboard is the enforcement point: it reads the principal from
the SSO proxy's verified headers and blocks actions the principal is not
permitted to take (HTTP 403).
"""
from __future__ import annotations

import os

from fastapi import HTTPException, Request
from pydantic import BaseModel

from agentic_cli.auth import (
    AuthorizationError,
    Principal,
    authorize,
    current_principal,
    resolve_provider,
)


class MeResponse(BaseModel):
    subject: str
    display_name: str = ""
    roles: list[str] = []
    permissions: list[str] = []
    groups: list[str] = []
    provider: str = "dev"
    authenticated: bool = True
    mode: str = "dev"


def principal_from_request(request: Request) -> Principal:
    """Resolve the current principal from request headers via the configured provider."""
    return current_principal(dict(request.headers))


def me(request: Request) -> MeResponse:
    p = principal_from_request(request)
    return MeResponse(
        subject=p.subject, display_name=p.display_name, roles=p.roles,
        permissions=sorted(p.permissions), groups=p.groups, provider=p.provider,
        authenticated=p.authenticated, mode=os.environ.get("DVA_AUTH_MODE", "dev"),
    )


def require(permission: str):
    """FastAPI dependency: allow the request only if the principal has ``permission``.

    Returns the principal on success; raises HTTP 403 (or 401 if unauthenticated)
    otherwise. Attach with ``Depends(require("knowledge:project"))``.
    """
    def _dep(request: Request) -> Principal:
        p = principal_from_request(request)
        try:
            authorize(p, permission)
        except AuthorizationError as e:
            code = 401 if not p.authenticated else 403
            raise HTTPException(status_code=code, detail=str(e))
        return p
    return _dep


def actor_of(request: Request) -> str:
    """Best-effort actor subject for audit attribution."""
    try:
        return principal_from_request(request).subject
    except Exception:  # noqa: BLE001
        return ""
