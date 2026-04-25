"""Dataset management for agent evaluation."""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class EvaluationSample:
    """A single test sample with input and expected output."""
    input: str
    expected_output: str
    sample_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class EvaluationDataset:
    """A dataset for evaluating agent performance."""
    id: str
    name: str
    description: str
    samples: List[EvaluationSample] = field(default_factory=list)
    created: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_sample(self, sample: EvaluationSample) -> None:
        """Add a sample to the dataset."""
        if not sample.sample_id:
            sample.sample_id = f"{self.id}-{len(self.samples)}"
        self.samples.append(sample)
        self.updated = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created": self.created,
            "updated": self.updated,
            "tags": self.tags,
            "metadata": self.metadata,
            "samples": [s.to_dict() for s in self.samples],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvaluationDataset":
        """Create from dictionary."""
        samples = [EvaluationSample(**s) for s in data.get("samples", [])]
        dataset = cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            created=data.get("created", datetime.now(timezone.utc).isoformat()),
            updated=data.get("updated", datetime.now(timezone.utc).isoformat()),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )
        dataset.samples = samples
        return dataset


class DatasetManager:
    """Manages evaluation datasets."""

    def __init__(self, datasets_dir: Path):
        """Initialize dataset manager."""
        self.datasets_dir = Path(datasets_dir)
        self.datasets_dir.mkdir(parents=True, exist_ok=True)

    def create_dataset(
        self,
        dataset_id: str,
        name: str,
        description: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvaluationDataset:
        """Create a new dataset."""
        dataset = EvaluationDataset(
            id=dataset_id,
            name=name,
            description=description,
            tags=tags or [],
            metadata=metadata or {},
        )
        self.save_dataset(dataset)
        return dataset

    def save_dataset(self, dataset: EvaluationDataset) -> Path:
        """Save dataset to disk."""
        dataset_file = self.datasets_dir / f"{dataset.id}.json"
        dataset_file.write_text(json.dumps(dataset.to_dict(), indent=2))
        return dataset_file

    def load_dataset(self, dataset_id: str) -> Optional[EvaluationDataset]:
        """Load dataset from disk."""
        dataset_file = self.datasets_dir / f"{dataset_id}.json"
        if not dataset_file.exists():
            return None
        data = json.loads(dataset_file.read_text())
        return EvaluationDataset.from_dict(data)

    def list_datasets(self) -> List[EvaluationDataset]:
        """List all datasets."""
        datasets = []
        for dataset_file in self.datasets_dir.glob("*.json"):
            data = json.loads(dataset_file.read_text())
            datasets.append(EvaluationDataset.from_dict(data))
        return sorted(datasets, key=lambda d: d.created, reverse=True)

    def delete_dataset(self, dataset_id: str) -> bool:
        """Delete a dataset."""
        dataset_file = self.datasets_dir / f"{dataset_id}.json"
        if dataset_file.exists():
            dataset_file.unlink()
            return True
        return False
