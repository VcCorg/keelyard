"""Glean configuration resolved from the environment (.env-backed).

Configured via ``dva init glean`` (token or SSO mode). Token mode is fully
functional; SSO mode records the OAuth issuer/client and defers live token
exchange to a production step (see docs/design/04-enterprise-auth.md stance).
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

    @classmethod
    def load(cls) -> "GleanConfig":
        return cls(
            api_url=os.environ.get("GLEAN_API_URL", "").strip().rstrip("/"),
            auth_mode=(os.environ.get("GLEAN_AUTH_MODE", "token").strip() or "token").lower(),
            api_token=os.environ.get("GLEAN_API_TOKEN", "").strip(),
            oauth_issuer=os.environ.get("GLEAN_OAUTH_ISSUER", "").strip(),
            oauth_client_id=os.environ.get("GLEAN_OAUTH_CLIENT_ID", "").strip(),
        )

    @property
    def is_token_mode(self) -> bool:
        return self.auth_mode != "sso"

    def is_configured(self) -> bool:
        if not self.api_url:
            return False
        if self.is_token_mode:
            return bool(self.api_token)
        return bool(self.oauth_issuer and self.oauth_client_id)

    def unavailable_reason(self) -> Optional[str]:
        """Human-readable reason Glean can't run a live query, or None if it can."""
        if not self.api_url:
            return "Glean not configured (GLEAN_API_URL unset). Run: dva init glean ..."
        if not self.is_token_mode:
            return ("Glean is in SSO mode — live OAuth token exchange is a production step. "
                    "Use token mode (dva init glean --url <> --token <>) to query now.")
        if not self.api_token:
            return "Glean token mode selected but GLEAN_API_TOKEN is unset."
        return None

    @property
    def search_url(self) -> str:
        return f"{self.api_url}/rest/api/v1/search"
