"""Identity + RBAC model — the vocabulary of enterprise auth.

Roles are ordered (viewer < developer < maintainer < admin); a role grants a
fixed set of permissions. Sensitive actions declare the permission they need,
and :func:`authorize` decides — the same model whether identity came from a dev
principal or an SSO proxy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

# ── Roles (ordered, least → most privileged) ─────────────────────────────────
VIEWER = "viewer"
DEVELOPER = "developer"
MAINTAINER = "maintainer"
ADMIN = "admin"

ROLE_ORDER = [VIEWER, DEVELOPER, MAINTAINER, ADMIN]


# ── Permissions ──────────────────────────────────────────────────────────────
# Read-only surfaces need none; these gate state-changing / vendor-facing actions.
PERM_CONTEXT_BUILD = "context:build"        # render a portable context bundle
PERM_SESSION_CREATE = "session:create"      # launch an execution engine session
PERM_KNOWLEDGE_PROJECT = "knowledge:project"  # project canonical knowledge to a vendor
PERM_KNOWLEDGE_DELETE = "knowledge:delete"  # delete/prune vendor knowledge
PERM_ADMIN = "admin:*"                       # administrative operations

ALL_PERMISSIONS = [
    PERM_CONTEXT_BUILD, PERM_SESSION_CREATE, PERM_KNOWLEDGE_PROJECT,
    PERM_KNOWLEDGE_DELETE, PERM_ADMIN,
]

# Each role grants its own permissions plus everything below it.
ROLE_PERMISSIONS: dict[str, set[str]] = {
    VIEWER: set(),
    DEVELOPER: {PERM_CONTEXT_BUILD, PERM_SESSION_CREATE},
    MAINTAINER: {PERM_CONTEXT_BUILD, PERM_SESSION_CREATE, PERM_KNOWLEDGE_PROJECT,
                 PERM_KNOWLEDGE_DELETE},
    ADMIN: set(ALL_PERMISSIONS),
}


def permissions_for(roles: Iterable[str]) -> set[str]:
    perms: set[str] = set()
    for r in roles:
        perms |= ROLE_PERMISSIONS.get(r, set())
    return perms


@dataclass
class Principal:
    """An authenticated identity resolved by an :class:`AuthProvider`."""
    subject: str                              # stable id (email / username)
    display_name: str = ""
    roles: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    provider: str = "dev"                     # which provider resolved this
    authenticated: bool = True

    @property
    def permissions(self) -> set[str]:
        return permissions_for(self.roles)

    def has(self, permission: str) -> bool:
        p = self.permissions
        return PERM_ADMIN in p or permission in p

    @classmethod
    def anonymous(cls) -> "Principal":
        return cls(subject="anonymous", display_name="Anonymous", roles=[],
                   provider="none", authenticated=False)


class AuthorizationError(PermissionError):
    """Raised when a principal lacks a required permission."""

    def __init__(self, principal: Principal, permission: str):
        self.principal = principal
        self.permission = permission
        super().__init__(
            f"'{principal.subject}' (roles: {', '.join(principal.roles) or 'none'}) "
            f"lacks required permission '{permission}'"
        )


def authorize(principal: Principal, permission: str) -> None:
    """Raise :class:`AuthorizationError` unless ``principal`` has ``permission``."""
    if not principal.has(permission):
        raise AuthorizationError(principal, permission)
