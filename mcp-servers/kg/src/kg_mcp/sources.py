"""Knowledge source registry for KG MCP Server.

Reads from the DVA CLI config file (~/.dva-agentic/config.json) as the single
source of truth for registered data sources. The CLI's `dva data create` command
is the primary way to register sources.
"""

import json
import logging
from pathlib import Path
from typing import Any

from .config import KGConfig

logger = logging.getLogger(__name__)

# Type name mapping: CLI uses short names, we normalize to descriptive names
_TYPE_MAP = {"doc": "document", "confluence": "confluence", "git": "git"}
_TYPE_MAP_REVERSE = {"document": "doc", "confluence": "confluence", "git": "git"}


class KnowledgeSource:
    """A registered knowledge source (read from DVA CLI config)."""

    def __init__(
        self,
        name: str,
        source_type: str,
        location: str,
        *,
        project: str = "",
        description: str = "",
        tags: list[str] | None = None,
        confluence_space: str = "",
        created_at: str = "",
        kg_status: str = "registered",
    ):
        self.name = name
        self.source_type = _TYPE_MAP.get(source_type, source_type)
        self.location = location
        self.project = project
        self.description = description
        self.tags = tags or []
        self.confluence_space = confluence_space
        self.created_at = created_at
        self.status = kg_status

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source_type": self.source_type,
            "location": self.location,
            "project": self.project,
            "description": self.description,
            "tags": self.tags,
            "confluence_space": self.confluence_space,
            "created_at": self.created_at,
            "status": self.status,
        }

    @classmethod
    def from_cli_dict(cls, data: dict[str, Any]) -> "KnowledgeSource":
        """Create from a DVA CLI config source entry."""
        return cls(
            name=data.get("name", ""),
            source_type=data.get("type", "doc"),
            location=data.get("location", ""),
            project=data.get("project", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            confluence_space=data.get("confluence_space", ""),
            created_at=data.get("created_at", ""),
            kg_status=data.get("kg_status", "registered"),
        )


class SourceRegistry:
    """Reads knowledge sources from DVA CLI config (~/.dva-agentic/config.json).

    The CLI's `dva data create` command is the primary registration method.
    This class provides read access + status updates for the kg-mcp server.
    """

    def __init__(self, config: KGConfig):
        self._path = Path(config.source_registry_path).expanduser()

    def _load_config(self) -> dict:
        """Load the full CLI config file."""
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except Exception as e:
                logger.error(f"Failed to load config from {self._path}: {e}")
        return {}

    def _save_config(self, config: dict):
        """Save the full CLI config file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(config, indent=2))

    def _get_sources_raw(self) -> list[dict]:
        """Get raw source entries from config."""
        config = self._load_config()
        return config.get("data", {}).get("sources", [])

    def get(self, name: str) -> KnowledgeSource | None:
        """Get a source by name."""
        for raw in self._get_sources_raw():
            if raw.get("name") == name:
                return KnowledgeSource.from_cli_dict(raw)
        return None

    def list_all(self, project: str | None = None) -> list[KnowledgeSource]:
        """List all sources, optionally filtered by project."""
        sources = [KnowledgeSource.from_cli_dict(s) for s in self._get_sources_raw()]
        if project:
            return [s for s in sources if s.project == project]
        return sources

    def update_status(self, name: str, status: str):
        """Update a source's kg_status in the config file."""
        config = self._load_config()
        sources = config.get("data", {}).get("sources", [])
        for source in sources:
            if source.get("name") == name:
                source["kg_status"] = status
                self._save_config(config)
                logger.info(f"Updated source '{name}' kg_status to '{status}'")
                return
        logger.warning(f"Source '{name}' not found for status update")
