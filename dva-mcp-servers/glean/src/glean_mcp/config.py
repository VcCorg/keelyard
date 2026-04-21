"""Configuration for Glean MCP."""

import os
from pydantic_settings import BaseSettings


class GleanConfig(BaseSettings):
    """Glean connection configuration."""

    api_token: str = ""
    domain: str = "https://example-production-be.glean.com"
    base_url: str = ""

    model_config = {
        "env_prefix": "GLEAN_",
        "env_file": ".env",
        "extra": "ignore",
    }

    @property
    def api_base_url(self) -> str:
        """REST API v1 base URL for Glean."""
        if self.base_url:
            return self.base_url
        return f"{self.domain.rstrip('/')}/mcp/rest/api/v1"

    @property
    def is_configured(self) -> bool:
        """Check if minimum configuration is present."""
        return bool(self.api_token and self.domain)

    @property
    def auth_headers(self) -> dict:
        """HTTP headers for authenticated requests."""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
