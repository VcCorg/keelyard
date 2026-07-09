"""OAuth token acquisition for Glean SSO mode.

Two ways to get an access token for Glean's REST API:

* on-behalf-of — a forwarded end-user access token (from the SSO proxy). Used
  as-is, so Glean applies that user's permissions (mirrors the IDE plugin).
* client-credentials — a service token minted from the IdP with the client
  id/secret. Used when there is no per-user token (CLI, background jobs).

The HTTP calls are thin; the response parsers are pure and unit-tested. Service
tokens are cached in-process until shortly before expiry.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Optional, Tuple

from agentic_cli.glean.config import GleanConfig

# (issuer, client_id) -> (access_token, expiry_epoch)
_CACHE: dict[Tuple[str, str], Tuple[str, float]] = {}
_LOCK = threading.Lock()
_EXPIRY_SKEW = 60.0  # refresh a minute before actual expiry


class OAuthError(RuntimeError):
    """Raised when an OAuth token cannot be obtained."""


def parse_discovery(data: Any) -> str:
    """Extract ``token_endpoint`` from an OIDC discovery document."""
    if isinstance(data, dict) and data.get("token_endpoint"):
        return str(data["token_endpoint"])
    raise OAuthError("OIDC discovery document has no token_endpoint.")


def parse_token_response(data: Any) -> Tuple[str, float]:
    """Return ``(access_token, expires_in_seconds)`` from a token response."""
    if not isinstance(data, dict) or not data.get("access_token"):
        raise OAuthError("Token response has no access_token.")
    try:
        expires_in = float(data.get("expires_in", 3600) or 3600)
    except (TypeError, ValueError):
        expires_in = 3600.0
    return str(data["access_token"]), expires_in


def _resolve_token_endpoint(cfg: GleanConfig, client) -> str:
    if cfg.oauth_token_url:
        return cfg.oauth_token_url
    # Try OAuth 2.0 Authorization Server metadata first (Glean's own OAuth
    # server publishes this), then fall back to OIDC discovery (IdP issuers).
    candidates = [cfg.oauth_metadata_url, cfg.discovery_url]
    last_err: Optional[str] = None
    for url in candidates:
        try:
            resp = client.get(url)
        except Exception as exc:  # noqa: BLE001
            last_err = f"{url}: {exc}"
            continue
        if resp.status_code >= 400:
            last_err = f"{url} returned {resp.status_code}"
            continue
        try:
            return parse_discovery(resp.json())
        except OAuthError as exc:
            last_err = f"{url}: {exc}"
            continue
    raise OAuthError(f"Could not resolve token endpoint via discovery ({last_err}).")


def fetch_client_credentials_token(cfg: GleanConfig) -> str:
    """Mint (or reuse a cached) service access token via client-credentials."""
    if not cfg.has_client_credentials:
        raise OAuthError("Client-credentials not configured (need issuer, client id, secret).")

    key = (cfg.oauth_server_base, cfg.oauth_client_id)
    now = time.time()
    with _LOCK:
        cached = _CACHE.get(key)
        if cached and cached[1] - _EXPIRY_SKEW > now:
            return cached[0]

    try:
        import httpx
    except Exception as exc:  # noqa: BLE001
        raise OAuthError("httpx is not available on the backend.") from exc

    data = {
        "grant_type": "client_credentials",
        "client_id": cfg.oauth_client_id,
        "client_secret": cfg.oauth_client_secret,
    }
    if cfg.oauth_scope:
        data["scope"] = cfg.oauth_scope

    try:
        with httpx.Client(timeout=15.0) as client:
            endpoint = _resolve_token_endpoint(cfg, client)
            resp = client.post(endpoint, data=data)
    except OAuthError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise OAuthError(f"Token request failed: {exc}") from exc

    if resp.status_code >= 400:
        raise OAuthError(f"Token endpoint returned {resp.status_code}: {resp.text[:200]}")
    token, expires_in = parse_token_response(resp.json())
    with _LOCK:
        _CACHE[key] = (token, time.time() + expires_in)
    return token


def access_token_for(cfg: GleanConfig, user_token: Optional[str] = None) -> str:
    """Best token for a Glean query: the user's token if provided, else a service token."""
    if user_token and user_token.strip():
        return user_token.strip()
    return fetch_client_credentials_token(cfg)


def clear_cache() -> None:
    with _LOCK:
        _CACHE.clear()
