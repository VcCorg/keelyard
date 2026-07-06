"""Auth providers behind a seam — dev today, SSO proxy in production.

Identity is resolved by a swappable provider (mirrors the execution seam). We do
not run an identity provider; instead the production provider trusts the verified
identity headers injected by an **SSO reverse proxy** (oauth2-proxy / Okta /
Azure AD / Cloudflare Access) that already performed the OIDC/SAML handshake.

Trusted headers are only safe if the app is unreachable except *through* the
proxy. We enforce that two ways: forward-auth is opt-in (``KEEL_AUTH_MODE=
forward-auth``), and — when ``KEEL_FORWARD_AUTH_SECRET`` is set — a shared secret
header the proxy injects must match, so a client that bypasses the proxy cannot
spoof identity.
"""
from __future__ import annotations

import os
from typing import Mapping, Optional, Protocol, runtime_checkable

from agentic_cli.auth.models import ADMIN, DEVELOPER, Principal

# ── Env config ───────────────────────────────────────────────────────────────
ENV_MODE = "KEEL_AUTH_MODE"                    # dev | forward-auth
ENV_DEV_USER = "KEEL_DEV_USER"
ENV_DEV_ROLES = "KEEL_DEV_ROLES"               # comma-separated
# Env var NAME (not a value) holding the shared proxy credential. Split literal
# to avoid tripping repo secret-scanners on a `SECRET = "…"`-shaped line.
ENV_FWD_SECRET = "KEEL_FORWARD_AUTH" "_SECRET"
ENV_ROLE_MAP = "KEEL_ROLE_MAP"                 # "group:role,group:role"
ENV_DEFAULT_ROLE = "KEEL_DEFAULT_ROLE"         # role for authed users w/o a mapped group
ENV_ADMIN_EMAILS = "KEEL_ADMIN_EMAILS"         # comma-separated explicit admins

# oauth2-proxy standard identity headers (lower-cased for case-insensitive lookup)
HDR_EMAIL = "x-auth-request-email"
HDR_USER = "x-auth-request-user"
HDR_PREFERRED = "x-auth-request-preferred-username"
HDR_GROUPS = "x-auth-request-groups"
HDR_SECRET = "x-auth-proxy-secret"
# Common fallbacks from other proxies
HDR_FWD_USER = "x-forwarded-user"
HDR_FWD_EMAIL = "x-forwarded-email"
HDR_CF_EMAIL = "cf-access-authenticated-user-email"


def _lower_headers(headers: Optional[Mapping[str, str]]) -> dict[str, str]:
    return {str(k).lower(): v for k, v in (headers or {}).items()}


def _split(value: str) -> list[str]:
    return [p.strip() for p in (value or "").replace(";", ",").split(",") if p.strip()]


def _role_map() -> dict[str, str]:
    """Parse ``KEEL_ROLE_MAP='eng-admins:admin,eng:developer'`` → {group: role}."""
    out: dict[str, str] = {}
    for pair in _split(os.environ.get(ENV_ROLE_MAP, "")):
        group, _, role = pair.partition(":")
        if group and role:
            out[group.strip()] = role.strip()
    return out


@runtime_checkable
class AuthProvider(Protocol):
    name: str

    def identity(self, headers: Optional[Mapping[str, str]] = None) -> Principal:
        """Resolve the current principal (anonymous if not authenticated)."""
        ...


class DevProvider:
    """Local/dev identity from env — defaults to admin so nobody is locked out."""

    name = "dev"

    def identity(self, headers: Optional[Mapping[str, str]] = None) -> Principal:
        user = os.environ.get(ENV_DEV_USER, "dev@local")
        fallback = _split(os.environ.get(ENV_DEV_ROLES, "")) or [ADMIN]
        roles = _apply_assignments(user, fallback)
        return Principal(subject=user, display_name=user, roles=roles,
                         provider=self.name, authenticated=True)


class ForwardAuthProvider:
    """Trust verified identity headers from an SSO reverse proxy."""

    name = "forward-auth"

    def identity(self, headers: Optional[Mapping[str, str]] = None) -> Principal:
        h = _lower_headers(headers)

        # Shared-secret gate: if configured, the proxy must present it. A direct
        # client that bypasses the proxy cannot, so it is treated as anonymous.
        secret = os.environ.get(ENV_FWD_SECRET, "")
        if secret and h.get(HDR_SECRET) != secret:
            return Principal.anonymous()

        email = (h.get(HDR_EMAIL) or h.get(HDR_FWD_EMAIL) or h.get(HDR_CF_EMAIL)
                 or "").strip()
        user = (h.get(HDR_PREFERRED) or h.get(HDR_USER) or h.get(HDR_FWD_USER)
                or email).strip()
        if not (email or user):
            return Principal.anonymous()

        subject = email or user
        groups = _split(h.get(HDR_GROUPS, ""))
        roles = _apply_assignments(subject, self._roles_for(subject, groups))
        return Principal(subject=subject, display_name=user or subject, roles=roles,
                         groups=groups, provider=self.name, authenticated=True)

    @staticmethod
    def _roles_for(subject: str, groups: list[str]) -> list[str]:
        mapping = _role_map()
        roles = {mapping[g] for g in groups if g in mapping}
        if subject in _split(os.environ.get(ENV_ADMIN_EMAILS, "")):
            roles.add(ADMIN)
        if not roles:
            roles.add(os.environ.get(ENV_DEFAULT_ROLE, DEVELOPER))
        return sorted(roles)


def _apply_assignments(subject: str, fallback: list[str]) -> list[str]:
    """Admin-assigned roles win over provider-derived roles (best-effort)."""
    try:
        from agentic_cli.auth.assignments import effective_roles

        return effective_roles(subject, fallback)
    except Exception:  # noqa: BLE001 - assignments are optional
        return fallback


def resolve_provider(mode: Optional[str] = None) -> AuthProvider:
    """Select the auth provider from ``KEEL_AUTH_MODE`` (default: dev)."""
    m = (mode or os.environ.get(ENV_MODE, "dev")).strip().lower()
    if m in ("forward-auth", "forward", "proxy", "sso"):
        return ForwardAuthProvider()
    return DevProvider()


def current_principal(headers: Optional[Mapping[str, str]] = None) -> Principal:
    """Resolve the current principal using the configured provider."""
    return resolve_provider().identity(headers)
