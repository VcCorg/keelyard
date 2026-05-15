"""Configuration for the Agentic Platform MCP server."""

import os
from pathlib import Path


class AgenticConfig:
    """Reads configuration from environment variables."""

    def __init__(self) -> None:
        # Tracker database — shared with the CLI
        self.tracker_db = Path(
            os.environ.get(
                "AGENTIC_TRACKER_DB",
                str(Path.home() / ".agent-cli-agentic" / "tracker.db"),
            )
        )

        # Skills registry path
        self.skills_registry = Path(
            os.environ.get(
                "SKILLS_REGISTRY_PATH",
                str(Path(__file__).resolve().parents[4] / "skills" / "registry.json"),
            )
        )

        # Skills directory (where SKILL.md files live)
        self.skills_dir = Path(
            os.environ.get(
                "SKILLS_DIR",
                str(Path(__file__).resolve().parents[4] / "skills" / "skills"),
            )
        )
