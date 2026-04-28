"""Configuration for Jira Server MCP."""

from pydantic_settings import BaseSettings


class JiraConfig(BaseSettings):
    """Jira Server connection settings.

    Reads from environment variables:
      - JIRA_SERVER_URL: Base URL of the Jira Server instance
      - JIRA_PERSONAL_ACCESS_TOKEN: Personal Access Token for authentication
      - JIRA_DEFAULT_PROJECT: Optional default project key
    """

    jira_server_url: str = ""
    jira_personal_access_token: str = ""
    jira_default_project: str = ""
    jira_verify_ssl: bool = True

    @property
    def is_configured(self) -> bool:
        return bool(self.jira_server_url and self.jira_personal_access_token)

    @property
    def api_base_url(self) -> str:
        """Base URL for Jira REST API v2."""
        return f"{self.jira_server_url.rstrip('/')}/rest/api/2"

    @property
    def auth_headers(self) -> dict[str, str]:
        """Authentication headers using Bearer token."""
        return {
            "Authorization": f"Bearer {self.jira_personal_access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
