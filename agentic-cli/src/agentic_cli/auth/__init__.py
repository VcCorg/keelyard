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
    PERM_PLATFORM_CONFIGURE,
    PERM_REQUIREMENTS_PUSH,
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
from agentic_cli.auth.assignments import (
    VALID_ROLES,
    effective_roles,
    get_roles,
    load_assignments,
    remove as remove_assignment,
    set_roles,
)
from agentic_cli.auth.persona import (
    BUILTIN_PERSONAS,
    DEFAULT_PERSONA,
    ROLE_PERSONA_DEFAULT,
    get_persona,
    load_persona_assignments,
    persona_for,
    persona_map,
    remove as remove_persona_assignment,
    set_persona,
)

__all__ = [
    "ADMIN", "MAINTAINER", "DEVELOPER", "VIEWER", "ROLE_ORDER",
    "ROLE_PERMISSIONS", "ALL_PERMISSIONS",
    "PERM_CONTEXT_BUILD", "PERM_SESSION_CREATE", "PERM_KNOWLEDGE_PROJECT",
    "PERM_KNOWLEDGE_DELETE", "PERM_REQUIREMENTS_PUSH",
    "PERM_PLATFORM_CONFIGURE", "PERM_ADMIN",
    "Principal", "AuthorizationError", "authorize", "permissions_for",
    "AuthProvider", "DevProvider", "ForwardAuthProvider",
    "resolve_provider", "current_principal",
    "VALID_ROLES", "load_assignments", "get_roles", "set_roles",
    "remove_assignment", "effective_roles",
    "BUILTIN_PERSONAS", "DEFAULT_PERSONA", "ROLE_PERSONA_DEFAULT",
    "persona_for", "persona_map", "get_persona", "set_persona",
    "load_persona_assignments", "remove_persona_assignment",
]
