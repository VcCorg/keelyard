"""Agent configuration — loaded from agent.json or environment variables.

This allows each agent instance to have its own model and GCP config
independent of the global DVA CLI config.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AgentConfig:
    """Configuration for the onboard agent."""

    model_name: str = "gemini-2.5-flash-lite"
    gcp_project_id: str | None = None
    gcp_location: str | None = None
    max_proposals: int = 10
    auto_accept: bool = False

    @classmethod
    def load(cls, config_path: Path | None = None) -> "AgentConfig":
        """Load config from agent.json, falling back to env vars.

        Priority: config_path > agent.json in agent dir > env vars > defaults
        """
        config = cls()

        # Try agent.json
        if config_path is None:
            config_path = Path(__file__).parent.parent / "agent.json"

        if config_path.exists():
            try:
                data = json.loads(config_path.read_text())
                config.model_name = data.get("model_name", config.model_name)
                config.gcp_project_id = data.get("gcp_project_id", config.gcp_project_id)
                config.gcp_location = data.get("gcp_location", config.gcp_location)
                config.max_proposals = data.get("max_proposals", config.max_proposals)
                config.auto_accept = data.get("auto_accept", config.auto_accept)
            except (json.JSONDecodeError, OSError):
                pass

        # Env var overrides
        config.model_name = os.environ.get("ONBOARD_AGENT_MODEL", config.model_name)
        config.gcp_project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", config.gcp_project_id)
        config.gcp_location = os.environ.get("GOOGLE_CLOUD_LOCATION", config.gcp_location)

        return config

    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "gcp_project_id": self.gcp_project_id,
            "gcp_location": self.gcp_location,
            "max_proposals": self.max_proposals,
            "auto_accept": self.auto_accept,
        }
