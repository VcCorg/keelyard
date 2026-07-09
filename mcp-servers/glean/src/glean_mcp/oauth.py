"""OAuth token acquisition for Glean MCP SSO mode.

Mints a service access token via the OAuth 2.0 client-credentials grant against
Glean's own OAuth Authorization Server (the tenant's ``/oauth/token`` endpoint),
then uses it as the Bearer token for Client API calls. This mirrors the CLI's
``agentic_cli.glean.oauth`` logic so the CLI (SSO) and the MCP authenticate the
same way.

Tokens are cached in-process until shortly before expiry to avoid minting a new
token on every tool call.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Tuple

import httpx

from .config import GleanConfig

logger = logging.getLogger(__name__)

# (token_url, client_id) -> (access_token, expiry_epoch)
_CACHE: dict[Tuple[str, str], Tuple[str, float]] = {}
_LOCK = asyncio.Lock()
_EXPIRY_SKEW = 60.0  # refresh a minute before actual expiry


class OAuthError(RuntimeError):
    """Raised when an OAuth token cannot be obtained."""


async def _discover_token_endpoint(config: GleanConfig, client: httpx.AsyncClient) -> str:
    """Resolve the token endpoint: explicit override, else OAuth server discovery."""
    if config.oauth_token_url:
        return config.oauth_token_url
    try:
        resp = await client.get(config.discovery_url)
    except Exception as exc:  # noqa: BLE001
        raise OAuthError(f"OAuth discovery failed at {config.discovery_url}: {exc}") from exc
    if resp.status_code >= 400:
        raise OAuthError(
            f"OAuth discovery returned {resp.status_code} at {config.discovery_url}."
        )
    data = resp.json()
    endpoint = data.get("token_endpoint") if isinstance(data, dict) else None
    if not endpoint:
        raise OAuthError("OAuth metadata document has no token_endpoint.")
    return str(endpoint)


async def fetch_service_token(config: GleanConfig) -> str:
    """Mint (or reuse a cached) service access token via client-credentials."""
    if not config.has_client_credentials:
        raise OAuthError(
            "Glean SSO needs GLEAN_OAUTH_CLIENT_ID and GLEAN_OAUTH_CLIENT_SECRET "
            "(and GLEAN_OAUTH_ISSUER or GLEAN_DOMAIN)."
        )

    token_url_key = config.oauth_token_url or config.discovery_url
    key = (token_url_key, config.oauth_client_id)
    now = time.time()

    async with _LOCK:
        cached = _CACHE.get(key)
        if cached and cached[1] - _EXPIRY_SKEW > now:
            return cached[0]

    data = {
        "grant_type": "client_credentials",
        "client_id": config.oauth_client_id,
        "client_secret": config.oauth_client_secret,
    }
    if config.oauth_scope:
        data["scope"] = config.oauth_scope

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            endpoint = await _discover_token_endpoint(config, client)
            resp = await client.post(endpoint, data=data)
    except OAuthError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise OAuthError(f"Token request failed: {exc}") from exc

    if resp.status_code >= 400:
        raise OAuthError(f"Token endpoint returned {resp.status_code}: {resp.text[:200]}")

    payload = resp.json()
    access_token = payload.get("access_token") if isinstance(payload, dict) else None
    if not access_token:
        raise OAuthError("Token response has no access_token.")
    try:
        expires_in = float(payload.get("expires_in", 3600) or 3600)
    except (TypeError, ValueError):
        expires_in = 3600.0

    async with _LOCK:
        _CACHE[key] = (str(access_token), time.time() + expires_in)
    logger.info("Obtained Glean service token via client-credentials (expires in %ss).", int(expires_in))
    return str(access_token)


async def bearer_token_for(config: GleanConfig) -> str:
    """Return the Bearer token to use: SSO service token, else the static API token."""
    if config.is_sso:
        return await fetch_service_token(config)
    return config.api_token


def clear_cache() -> None:
    _CACHE.clear()
