"""Configuration for Confluence MCP."""

from pydantic_settings import BaseSettings


class ConfluenceConfig(BaseSettings):
    """Confluence Server connection configuration."""

    server_url: str = "https://confluence.example.com"
    personal_access_token: str = ""
    default_space: str = ""
    verify_ssl: bool = True

    model_config = {
        "env_prefix": "CONFLUENCE_",
        "env_file": ".env",
        "extra": "ignore",
    }

    @property
    def api_base_url(self) -> str:
        """REST API base URL for Confluence Server."""
        return f"{self.server_url.rstrip('/')}/rest/api"

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
