"""Glean configuration resolved from the environment (.env-backed).

Configured via ``keel init glean`` (token or SSO mode). Both are functional:

* token — a Glean API token.
* sso   — OAuth. A live query needs an access token, obtained either by the
          client-credentials flow (service account: issuer + client id + secret)
          or by forwarding the signed-in user's access token (on-behalf-of).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class GleanConfig:
    api_url: str = ""
    auth_mode: str = "token"          # token | sso
    api_token: str = ""
    oauth_issuer: str = ""
    oauth_client_id: str = ""
    oauth_client_secret: str = ""
    oauth_scope: str = ""
    oauth_token_url: str = ""         # explicit token endpoint (else OIDC discovery)

    @classmethod
    def load(cls) -> "GleanConfig":
        return cls(
            api_url=os.environ.get("GLEAN_API_URL", "").strip().rstrip("/"),
            auth_mode=(os.environ.get("GLEAN_AUTH_MODE", "token").strip() or "token").lower(),
            api_token=os.environ.get("GLEAN_API_TOKEN", "").strip(),
            oauth_issuer=os.environ.get("GLEAN_OAUTH_ISSUER", "").strip().rstrip("/"),
            oauth_client_id=os.environ.get("GLEAN_OAUTH_CLIENT_ID", "").strip(),
            oauth_client_secret=os.environ.get("GLEAN_OAUTH_CLIENT_SECRET", "").strip(),
            oauth_scope=os.environ.get("GLEAN_OAUTH_SCOPE", "").strip(),
            oauth_token_url=os.environ.get("GLEAN_OAUTH_TOKEN_URL", "").strip(),
        )

    @property
    def is_token_mode(self) -> bool:
        return self.auth_mode != "sso"

    @property
    def has_client_credentials(self) -> bool:
        """True if a service token can be minted without a per-user token."""
        return bool(self.oauth_issuer and self.oauth_client_id and self.oauth_client_secret)

    def is_configured(self) -> bool:
        if not self.api_url:
            return False
        if self.is_token_mode:
            return bool(self.api_token)
        return bool(self.oauth_issuer and self.oauth_client_id)

    def unavailable_reason(self, user_token: Optional[str] = None) -> Optional[str]:
        """Human-readable reason Glean can't run a live query, or None if it can.

        ``user_token`` is a forwarded end-user access token (on-behalf-of); when
        present, SSO can query as that user without client credentials.
        """
        if not self.api_url:
            return "Glean not configured (GLEAN_API_URL unset). Run: keel init glean ..."
        if self.is_token_mode:
            if not self.api_token:
                return "Glean token mode selected but GLEAN_API_TOKEN is unset."
            return None
        # SSO mode
        if user_token:
            return None  # on-behalf-of the signed-in user
        if self.has_client_credentials:
            return None  # service token via client-credentials
        return ("Glean SSO needs a client secret for service auth "
                "(keel init glean --sso --client-secret <>), or a forwarded user token.")

    @property
    def search_url(self) -> str:
        return f"{self.api_url}/rest/api/v1/search"

    @property
    def discovery_url(self) -> str:
        return f"{self.oauth_issuer}/.well-known/openid-configuration"
