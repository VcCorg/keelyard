"""Enterprise auth — swappable identity providers + RBAC over the audit trail."""

from agentic_cli.auth.models import (
    ADMIN,
    ALL_PERMISSIONS,
    DEVELOPER,
    MAINTAINER,
    PERM_ADMIN,
    PERM_CONTEXT_BUILD,
    PERM_KNOWLEDGE_DELETE,
    PERM_KNOWLEDGE_PROJECT,
    PERM_SESSION_CREATE,
    ROLE_ORDER,
    ROLE_PERMISSIONS,
    VIEWER,
    AuthorizationError,
    Principal,
    authorize,
    permissions_for,
)
from agentic_cli.auth.providers import (
    AuthProvider,
    DevProvider,
    ForwardAuthProvider,
    current_principal,
    resolve_provider,
)

__all__ = [
    "ADMIN", "MAINTAINER", "DEVELOPER", "VIEWER", "ROLE_ORDER",
    "ROLE_PERMISSIONS", "ALL_PERMISSIONS",
    "PERM_CONTEXT_BUILD", "PERM_SESSION_CREATE", "PERM_KNOWLEDGE_PROJECT",
    "PERM_KNOWLEDGE_DELETE", "PERM_ADMIN",
    "Principal", "AuthorizationError", "authorize", "permissions_for",
    "AuthProvider", "DevProvider", "ForwardAuthProvider",
    "resolve_provider", "current_principal",
]
