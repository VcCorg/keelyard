"""Reusable evaluation configurations.

An :class:`EvaluationConfig` binds together a dataset, the metrics to compute,
and the framework/judge to use. Configs are persisted as YAML so they can be
versioned and re-run (e.g. ``keel eval create``, ``keel eval run agent``).
"""

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class EvaluationConfig:
    """A saved, reusable evaluation configuration."""

    name: str
    dataset: str
    metrics: List[str] = field(default_factory=list)
    framework: str = "builtin"
    judge: str = "none"
    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None
    description: str = ""
    created: str = field(default_factory=_now)
    updated: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a plain dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvaluationConfig":
        """Create from a dictionary, ignoring unknown keys."""
        known = {
            "name",
            "dataset",
            "metrics",
            "framework",
            "judge",
            "llm_model",
            "embedding_model",
            "description",
            "created",
            "updated",
            "metadata",
        }
        filtered = {k: v for k, v in (data or {}).items() if k in known}
        return cls(**filtered)


class EvalConfigManager:
    """Persists and retrieves :class:`EvaluationConfig` objects as YAML files."""

    def __init__(self, configs_dir: Path):
        """Initialize the manager.

        Args:
            configs_dir: Directory in which to store ``<name>.yaml`` configs.
        """
        self.configs_dir = Path(configs_dir)
        self.configs_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        return self.configs_dir / f"{name}.yaml"

    def exists(self, name: str) -> bool:
        """Return True if a config with ``name`` exists."""
        return self._path(name).exists()

    def save(self, config: EvaluationConfig) -> Path:
        """Persist a config to disk, updating its ``updated`` timestamp."""
        config.updated = _now()
        path = self._path(config.name)
        path.write_text(yaml.safe_dump(config.to_dict(), sort_keys=False))
        logger.debug(f"Saved eval config to {path}")
        return path

    def load(self, name: str) -> Optional[EvaluationConfig]:
        """Load a config by name, or None if it does not exist."""
        path = self._path(name)
        if not path.exists():
            return None
        data = yaml.safe_load(path.read_text()) or {}
        return EvaluationConfig.from_dict(data)

    def list(self) -> List[EvaluationConfig]:
        """Return all saved configs, newest first."""
        configs: List[EvaluationConfig] = []
        for path in self.configs_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(path.read_text()) or {}
                configs.append(EvaluationConfig.from_dict(data))
            except Exception as e:  # pragma: no cover - defensive
                logger.warning(f"Skipping invalid config {path}: {e}")
        return sorted(configs, key=lambda c: c.created, reverse=True)

    def delete(self, name: str) -> bool:
        """Delete a config by name. Returns True if a file was removed."""
        path = self._path(name)
        if path.exists():
            path.unlink()
            return True
        return False
