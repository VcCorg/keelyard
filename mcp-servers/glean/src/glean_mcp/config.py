"""Configuration for Glean MCP.

Supports two auth modes (parity with the CLI's Glean config):

* token — a static Glean API token (Authorization: Bearer <token>).
* sso   — OAuth client-credentials against Glean's own OAuth Authorization
          Server. A short-lived service access token is minted from
          GLEAN_OAUTH_TOKEN_URL (or discovered) using the client id/secret,
          then used as the Bearer token. See oauth.py.
"""

import os
from pydantic_settings import BaseSettings


class GleanConfig(BaseSettings):
    """Glean connection configuration."""

    api_token: str = ""
    domain: str = "https://example-production-be.glean.com"
    base_url: str = ""

    # Auth mode + OAuth (client-credentials) settings for SSO.
    auth_mode: str = "token"          # token | sso
    oauth_issuer: str = ""            # OAuth server base (defaults to domain)
    oauth_client_id: str = ""
    oauth_client_secret: str = ""
    oauth_scope: str = ""             # space-separated, e.g. "search mcp chat"
    oauth_token_url: str = ""         # explicit token endpoint (else discovery)

    model_config = {
        "env_prefix": "GLEAN_",
        "env_file": ".env",
        "extra": "ignore",
    }

    @property
    def is_sso(self) -> bool:
        return (self.auth_mode or "token").strip().lower() == "sso"

    @property
    def has_client_credentials(self) -> bool:
        """True if a service token can be minted without a per-user token."""
        return bool(self.oauth_issuer and self.oauth_client_id and self.oauth_client_secret) \
            or bool(self.domain and self.oauth_client_id and self.oauth_client_secret)

    @property
    def oauth_server_base(self) -> str:
        """Base URL of the OAuth Authorization Server (issuer, else the domain)."""
        return (self.oauth_issuer or self.domain).rstrip("/")

    @property
    def discovery_url(self) -> str:
        return f"{self.oauth_server_base}/.well-known/oauth-authorization-server"

    @property
    def api_base_url(self) -> str:
        """REST API v1 base URL for Glean."""
        if self.base_url:
            return self.base_url
        return f"{self.domain.rstrip('/')}/mcp/rest/api/v1"

    @property
    def is_configured(self) -> bool:
        """Check if minimum configuration is present."""
        if not self.domain:
            return False
        if self.is_sso:
            return self.has_client_credentials
        return bool(self.api_token)

    def headers_for(self, bearer_token: str) -> dict:
        """HTTP headers for authenticated requests using the given bearer token."""
        return {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @property
    def auth_headers(self) -> dict:
        """Static token-mode headers (kept for backwards compatibility)."""
        return self.headers_for(self.api_token)
