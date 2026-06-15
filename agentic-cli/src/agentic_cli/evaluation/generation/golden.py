"""Golden (reference / human-approved) dataset tracking.

A golden dataset is a specific dataset name+version that has been reviewed and
blessed as the trusted baseline for evaluation. This module maintains a small
JSON registry alongside the CSV datasets so golden status survives across runs
without altering the CSV files themselves.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_REGISTRY_FILENAME = "_golden.json"


@dataclass
class GoldenEntry:
    """A golden dataset marker."""

    dataset: str
    version: int
    marked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    note: str = ""

    def to_dict(self) -> Dict:
        return {"dataset": self.dataset, "version": self.version,
                "marked_at": self.marked_at, "note": self.note}


class GoldenRegistry:
    """Persists golden dataset markers in a JSON file."""

    def __init__(self, datasets_dir: Path):
        self.datasets_dir = Path(datasets_dir)
        self.datasets_dir.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.datasets_dir / _REGISTRY_FILENAME

    def _load(self) -> Dict[str, Dict]:
        if not self.registry_path.exists():
            return {}
        try:
            return json.loads(self.registry_path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, data: Dict[str, Dict]) -> None:
        self.registry_path.write_text(json.dumps(data, indent=2))

    def mark(self, dataset: str, version: int, note: str = "") -> GoldenEntry:
        """Mark a dataset version as golden (overwrites any prior marker)."""
        data = self._load()
        entry = GoldenEntry(dataset=dataset, version=version, note=note)
        data[dataset] = entry.to_dict()
        self._save(data)
        return entry

    def unmark(self, dataset: str) -> bool:
        """Remove a golden marker. Returns True if one existed."""
        data = self._load()
        if dataset in data:
            del data[dataset]
            self._save(data)
            return True
        return False

    def get(self, dataset: str) -> Optional[GoldenEntry]:
        """Return the golden entry for a dataset, if any."""
        data = self._load()
        if dataset in data:
            return GoldenEntry(**data[dataset])
        return None

    def is_golden(self, dataset: str, version: Optional[int] = None) -> bool:
        """Return True if the dataset (optionally a specific version) is golden."""
        entry = self.get(dataset)
        if not entry:
            return False
        return version is None or entry.version == version

    def list(self) -> List[GoldenEntry]:
        """Return all golden entries."""
        return [GoldenEntry(**v) for v in self._load().values()]
