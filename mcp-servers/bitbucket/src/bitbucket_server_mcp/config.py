"""Configuration for Bitbucket Server MCP."""

import os
from pydantic_settings import BaseSettings


class BitbucketConfig(BaseSettings):
    """Bitbucket Server connection configuration."""

    server_url: str = "https://bitbucket.example.com"
    personal_access_token: str = ""
    default_project: str = ""
    default_repo: str = ""
    verify_ssl: bool = True

    model_config = {
        "env_prefix": "BITBUCKET_",
        "env_file": ".env",
        "extra": "ignore",
    }

    @property
    def api_base_url(self) -> str:
        """REST API 1.0 base URL for Bitbucket Server."""
        return f"{self.server_url.rstrip('/')}/rest/api/1.0"

    @property
    def is_configured(self) -> bool:
        """Check if minimum configuration is present."""
        return bool(self.server_url and self.personal_access_token)

    @property
    def auth_headers(self) -> dict:
        """HTTP headers for authenticated requests."""
        return {
            "Authorization": f"Bearer {self.personal_access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
