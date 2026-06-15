"""CSV datasets with a Ragas-compatible schema and simple versioning.

Schema columns (Ragas convention):
    - ``user_input``        : the question / prompt (required)
    - ``reference_contexts``: JSON-encoded list of context strings (optional)
    - ``reference``         : ground-truth answer (optional)
    - ``response``          : agent answer (optional; filled by response collection)

Datasets are versioned on disk as ``<name>_v<N>.csv``. Registering a new CSV or
collecting agent responses creates a new version, preserving prior runs.
"""

import csv
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CSV_COLUMNS = ["user_input", "reference_contexts", "reference", "response"]
_VERSION_RE = re.compile(r"^(?P<name>.+)_v(?P<version>\d+)\.csv$")


@dataclass
class CsvRow:
    """A single row in a CSV dataset."""

    user_input: str
    reference_contexts: List[str] = field(default_factory=list)
    reference: str = ""
    response: str = ""

    def to_csv_dict(self) -> Dict[str, str]:
        """Serialize to a CSV-writable dict (lists JSON-encoded)."""
        return {
            "user_input": self.user_input,
            "reference_contexts": json.dumps(self.reference_contexts),
            "reference": self.reference,
            "response": self.response,
        }

    @classmethod
    def from_csv_dict(cls, data: Dict[str, str]) -> "CsvRow":
        """Parse from a CSV row dict, tolerating missing/plain context cells."""
        raw_ctx = (data.get("reference_contexts") or "").strip()
        contexts: List[str] = []
        if raw_ctx:
            try:
                parsed = json.loads(raw_ctx)
                contexts = parsed if isinstance(parsed, list) else [str(parsed)]
            except (json.JSONDecodeError, ValueError):
                contexts = [raw_ctx]
        return cls(
            user_input=(data.get("user_input") or "").strip(),
            reference_contexts=contexts,
            reference=(data.get("reference") or "").strip(),
            response=(data.get("response") or "").strip(),
        )


class CsvDatasetManager:
    """Reads and writes versioned CSV datasets in a directory."""

    def __init__(self, datasets_dir: Path):
        """Initialize the manager.

        Args:
            datasets_dir: Directory containing ``<name>_v<N>.csv`` files.
        """
        self.datasets_dir = Path(datasets_dir)
        self.datasets_dir.mkdir(parents=True, exist_ok=True)

    # -- version discovery ---------------------------------------------------

    def list_versions(self, name: str) -> List[int]:
        """Return sorted version numbers available for a dataset name."""
        versions = []
        for path in self.datasets_dir.glob(f"{name}_v*.csv"):
            m = _VERSION_RE.match(path.name)
            if m and m.group("name") == name:
                versions.append(int(m.group("version")))
        return sorted(versions)

    def latest_version(self, name: str) -> Optional[int]:
        """Return the highest version number, or None if none exist."""
        versions = self.list_versions(name)
        return versions[-1] if versions else None

    def list_datasets(self) -> Dict[str, List[int]]:
        """Map each dataset name to its list of versions."""
        result: Dict[str, List[int]] = {}
        for path in self.datasets_dir.glob("*_v*.csv"):
            m = _VERSION_RE.match(path.name)
            if not m:
                continue
            result.setdefault(m.group("name"), []).append(int(m.group("version")))
        return {k: sorted(v) for k, v in result.items()}

    def path_for(self, name: str, version: int) -> Path:
        """Return the file path for a specific dataset version."""
        return self.datasets_dir / f"{name}_v{version}.csv"

    # -- read / write --------------------------------------------------------

    def read(self, name: str, version: Optional[int] = None) -> List[CsvRow]:
        """Read rows for a dataset version (latest if not specified)."""
        if version is None:
            version = self.latest_version(name)
        if version is None:
            raise FileNotFoundError(f"No versions found for dataset '{name}'")
        path = self.path_for(name, version)
        if not path.exists():
            raise FileNotFoundError(f"Dataset version not found: {path}")
        rows: List[CsvRow] = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for raw in reader:
                rows.append(CsvRow.from_csv_dict(raw))
        return rows

    def write_new_version(self, name: str, rows: List[CsvRow]) -> int:
        """Write rows as the next version of a dataset. Returns the version."""
        next_version = (self.latest_version(name) or 0) + 1
        path = self.path_for(name, next_version)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for row in rows:
                writer.writerow(row.to_csv_dict())
        logger.debug(f"Wrote {len(rows)} rows to {path}")
        return next_version

    def register_from_file(self, name: str, source_csv: Path) -> int:
        """Import an external CSV as a new version, normalizing the schema.

        Args:
            name: Logical dataset name.
            source_csv: Path to a CSV with at least a ``user_input`` column.

        Returns:
            The new version number.

        Raises:
            FileNotFoundError: If the source file does not exist.
            ValueError: If the source CSV lacks a ``user_input`` column.
        """
        source_csv = Path(source_csv)
        if not source_csv.exists():
            raise FileNotFoundError(f"Source CSV not found: {source_csv}")
        with open(source_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            if "user_input" not in fieldnames:
                raise ValueError(
                    "Source CSV must contain a 'user_input' column. "
                    f"Found columns: {', '.join(fieldnames) or '(none)'}"
                )
            rows = [CsvRow.from_csv_dict(raw) for raw in reader]
        return self.write_new_version(name, rows)

    @staticmethod
    def has_responses(rows: List[CsvRow]) -> bool:
        """Return True if every row already has a non-empty response."""
        return bool(rows) and all(r.response.strip() for r in rows)
