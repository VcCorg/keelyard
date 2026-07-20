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
    # Resolved persona (dev/qa/ba/sm/domain) — drives persona-scoped skill
    # governance and persona-aware navigation.
    persona: str = "dev"


def principal_from_request(request: Request) -> Principal:
    """Resolve the current principal from request headers via the configured provider."""
    return current_principal(dict(request.headers))


def me(request: Request) -> MeResponse:
    p = principal_from_request(request)
    try:
        from agentic_cli.auth import persona_for

        persona = persona_for(p)
    except Exception:  # noqa: BLE001 - never break /me on persona resolution
        persona = "dev"
    return MeResponse(
        subject=p.subject, display_name=p.display_name, roles=p.roles,
        permissions=sorted(p.permissions), groups=p.groups, provider=p.provider,
        authenticated=p.authenticated, mode=os.environ.get("KEEL_AUTH_MODE", "dev"),
        persona=persona,
    )


# ── RBAC model (roles → permissions, personas) for the Identity & Access UI ──

# Human-readable blurbs for the permission slugs the CLI defines.
_PERMISSION_HELP = {
    "context:build": "Render a portable, engine-neutral context bundle.",
    "session:create": "Launch a session on an execution engine (Devin/local).",
    "knowledge:project": "Project canonical knowledge to a vendor / promote skills.",
    "knowledge:delete": "Delete or prune vendor knowledge.",
    "requirements:push": "Push approved stories to Jira (BA/SM).",
    "platform:configure": "Configure MCP servers, integrations and setup.",
    "admin:*": "All administrative operations.",
}

_PERSONA_HELP = {
    "dev": "Developer — builds under governed workflows.",
    "qa": "Quality — trials and evaluates skills.",
    "ba": "Business analyst — shapes requirements.",
    "sm": "Scrum master — drives delivery.",
    "domain": "Domain lead — owns governance for a domain.",
}


class PermissionInfo(BaseModel):
    permission: str
    description: str = ""


class RoleInfo(BaseModel):
    role: str
    permissions: list[str] = []
    read_only: bool = False


class PersonaInfo(BaseModel):
    persona: str
    description: str = ""


class RbacModel(BaseModel):
    roles: list[RoleInfo] = []
    permissions: list[PermissionInfo] = []
    personas: list[PersonaInfo] = []


def rbac_model() -> RbacModel:
    """The RBAC model the CLI defines — roles, permissions, personas — for the UI."""
    from agentic_cli.auth import ALL_PERMISSIONS, ROLE_ORDER, ROLE_PERMISSIONS

    try:
        from agentic_cli.auth import BUILTIN_PERSONAS
    except Exception:  # noqa: BLE001
        BUILTIN_PERSONAS = ("dev", "qa", "ba", "sm", "domain")

    roles = [
        RoleInfo(role=r, permissions=sorted(ROLE_PERMISSIONS.get(r, set())),
                 read_only=not ROLE_PERMISSIONS.get(r))
        for r in ROLE_ORDER
    ]
    perms = [PermissionInfo(permission=p, description=_PERMISSION_HELP.get(p, ""))
             for p in ALL_PERMISSIONS]
    personas = [PersonaInfo(persona=p, description=_PERSONA_HELP.get(p, ""))
                for p in BUILTIN_PERSONAS]
    return RbacModel(roles=roles, permissions=perms, personas=personas)


class PermissionCheck(BaseModel):
    subject: str
    permission: str
    allowed: bool
    roles: list[str] = []


def check_permission(request: Request, permission: str) -> PermissionCheck:
    """Whether the current principal has ``permission`` (mirrors `keel auth check`)."""
    p = principal_from_request(request)
    return PermissionCheck(subject=p.subject, permission=permission,
                           allowed=p.has(permission), roles=p.roles)


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
