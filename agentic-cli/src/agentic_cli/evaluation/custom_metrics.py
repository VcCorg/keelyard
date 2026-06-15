"""User-registered, prompt-based (LLM-as-Judge) custom metrics.

A custom metric is defined by a name and a natural-language scoring prompt
(criteria). When evaluated with the builtin framework and an available LLM
judge, the judge scores responses against the prompt on a 1-5 scale. Without a
judge, custom metrics fall back to a neutral score (so pipelines never break).

Metrics are persisted as YAML so they can be shared and versioned.
"""

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class CustomMetric:
    """A prompt-based custom metric definition."""

    name: str
    prompt: str
    description: str = ""
    scale_min: float = 1.0
    scale_max: float = 5.0
    schema: Dict[str, Any] = field(default_factory=dict)
    created: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CustomMetric":
        known = {"name", "prompt", "description", "scale_min", "scale_max", "schema", "created"}
        return cls(**{k: v for k, v in (data or {}).items() if k in known})


class CustomMetricManager:
    """Persists and retrieves :class:`CustomMetric` definitions as YAML."""

    def __init__(self, metrics_dir: Path):
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        return self.metrics_dir / f"{name}.yaml"

    def exists(self, name: str) -> bool:
        return self._path(name).exists()

    def register(self, metric: CustomMetric) -> Path:
        """Persist a custom metric definition."""
        path = self._path(metric.name)
        path.write_text(yaml.safe_dump(metric.to_dict(), sort_keys=False))
        logger.debug(f"Registered custom metric '{metric.name}' at {path}")
        return path

    def unregister(self, name: str) -> bool:
        """Delete a custom metric. Returns True if it existed."""
        path = self._path(name)
        if path.exists():
            path.unlink()
            return True
        return False

    def load(self, name: str) -> Optional[CustomMetric]:
        """Load a custom metric by name."""
        path = self._path(name)
        if not path.exists():
            return None
        return CustomMetric.from_dict(yaml.safe_load(path.read_text()) or {})

    def list(self) -> List[CustomMetric]:
        """Return all registered custom metrics."""
        metrics: List[CustomMetric] = []
        for path in self.metrics_dir.glob("*.yaml"):
            try:
                metrics.append(CustomMetric.from_dict(yaml.safe_load(path.read_text()) or {}))
            except Exception as e:  # pragma: no cover - defensive
                logger.warning(f"Skipping invalid custom metric {path}: {e}")
        return sorted(metrics, key=lambda m: m.name)

    def as_prompt_map(self) -> Dict[str, str]:
        """Return a mapping of metric name -> scoring prompt for all metrics."""
        return {m.name: m.prompt for m in self.list()}
