"""Storage and retrieval of agent evaluation run results.

`keel eval run agent` writes a JSON result file per run into the evaluations
directory. This module provides a typed view over those files so that the
`compare` and `report` commands can load and analyze prior runs.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EvalRunResult:
    """A single saved agent-evaluation run."""

    eval_id: str
    eval_name: str
    agent: str
    dataset: str
    dataset_version: Optional[int]
    framework: str
    judge: str
    metrics: List[str]
    timestamp: str
    num_rows: int
    aggregate: Dict[str, float] = field(default_factory=dict)
    metric_ranges: Dict[str, Any] = field(default_factory=dict)
    per_row: List[Dict[str, float]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    source_path: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any], source_path: Optional[str] = None) -> "EvalRunResult":
        """Build from the JSON structure written by `eval run agent`."""
        scores = data.get("scores", {}) or {}
        return cls(
            eval_id=data.get("eval_id", ""),
            eval_name=data.get("eval_name", ""),
            agent=data.get("agent", ""),
            dataset=data.get("dataset", ""),
            dataset_version=data.get("dataset_version"),
            framework=data.get("framework", ""),
            judge=data.get("judge", ""),
            metrics=data.get("metrics", []),
            timestamp=data.get("timestamp", ""),
            num_rows=data.get("num_rows", 0),
            aggregate=scores.get("aggregate", {}),
            metric_ranges=scores.get("metric_ranges", {}),
            per_row=scores.get("per_row", []),
            errors=scores.get("errors", []),
            source_path=source_path,
        )

    def normalized_aggregate(self) -> Dict[str, float]:
        """Aggregate scores normalized to 0-1 using declared metric ranges."""
        out: Dict[str, float] = {}
        for name, value in self.aggregate.items():
            rng = self.metric_ranges.get(name)
            if rng and len(rng) == 2 and rng[1] != rng[0]:
                low, high = rng[0], rng[1]
                out[name] = max(0.0, min(1.0, (value - low) / (high - low)))
            else:
                out[name] = value
        return out

    def overall_score(self) -> float:
        """Mean of normalized aggregate scores (0-1), or 0 if none."""
        norm = self.normalized_aggregate()
        return sum(norm.values()) / len(norm) if norm else 0.0


class EvalResultStore:
    """Reads agent-evaluation result JSON files from a directory."""

    def __init__(self, evals_dir: Path):
        """Initialize the store.

        Args:
            evals_dir: Directory containing ``*.json`` run-result files.
        """
        self.evals_dir = Path(evals_dir)
        self.evals_dir.mkdir(parents=True, exist_ok=True)

    def list(self) -> List[EvalRunResult]:
        """Return all agent-eval run results, newest first."""
        results: List[EvalRunResult] = []
        for path in self.evals_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError) as e:
                logger.debug(f"Skipping unreadable result {path}: {e}")
                continue
            # Only consider agent-eval results (they carry an 'agent' field).
            if "agent" not in data or "scores" not in data:
                continue
            results.append(EvalRunResult.from_dict(data, source_path=str(path)))
        return sorted(results, key=lambda r: r.timestamp, reverse=True)

    def load(self, eval_id: str) -> Optional[EvalRunResult]:
        """Load a single run result by its eval_id."""
        path = self.evals_dir / f"{eval_id}.json"
        if not path.exists():
            # Fall back to scanning (eval_id may differ from filename).
            for r in self.list():
                if r.eval_id == eval_id:
                    return r
            return None
        data = json.loads(path.read_text())
        return EvalRunResult.from_dict(data, source_path=str(path))

    def for_eval(self, eval_name: str) -> List[EvalRunResult]:
        """Return all runs for a given eval config name, newest first."""
        return [r for r in self.list() if r.eval_name == eval_name]

    def latest_per_agent(self, eval_name: str) -> Dict[str, EvalRunResult]:
        """Return the most recent run per agent for an eval config."""
        latest: Dict[str, EvalRunResult] = {}
        for r in self.for_eval(eval_name):  # already newest-first
            if r.agent not in latest:
                latest[r.agent] = r
        return latest
