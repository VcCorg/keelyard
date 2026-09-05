"""Pluggable evaluation framework abstraction.

A framework computes metric scores for a set of evaluation rows (input,
reference/expected, and the agent's response). This abstraction lets the CLI
swap between the built-in scorer (zero extra dependencies) and richer backends
such as Ragas (added in a later phase) without changing the command layer.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EvalRow:
    """A single evaluation row to be scored.

    Attributes:
        input_text: The user input / question.
        reference: The reference (expected/ground-truth) answer. May be empty
            for reference-free metrics.
        response: The agent's actual response to score.
        retrieved_contexts: Optional contexts the agent retrieved (used by
            context-based metrics in richer frameworks).
        row_id: Optional stable identifier for the row.
    """

    input_text: str
    reference: str = ""
    response: str = ""
    retrieved_contexts: List[str] = field(default_factory=list)
    row_id: Optional[str] = None


@dataclass
class EvalScores:
    """Result of a framework evaluation.

    Attributes:
        per_row: List of dicts (one per row) mapping metric name -> score.
        aggregate: Mapping of metric name -> aggregate (mean) score.
        metric_ranges: Mapping of metric name -> (min, max) score range, so
            consumers can normalize/interpret scores from different frameworks
            (e.g. builtin 0-1 vs Ragas 1-5).
        framework: Name of the framework that produced the scores.
        errors: Any non-fatal errors encountered during scoring.
    """

    per_row: List[Dict[str, float]] = field(default_factory=list)
    aggregate: Dict[str, float] = field(default_factory=dict)
    metric_ranges: Dict[str, Any] = field(default_factory=dict)
    framework: str = ""
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        return {
            "framework": self.framework,
            "aggregate": self.aggregate,
            "metric_ranges": self.metric_ranges,
            "per_row": self.per_row,
            "errors": self.errors,
        }


class EvalFramework(ABC):
    """Base class for evaluation frameworks."""

    #: Short, unique framework name (e.g. "builtin", "ragas").
    name: str = "base"

    def available(self) -> bool:
        """True when this framework can actually score right now.

        Distinct from constructing it. Optional frameworks import their heavy
        dependencies lazily, so the constructor succeeds and only ``evaluate``
        fails — which is too late for a caller deciding whether to fall back.
        """
        return True

    @abstractmethod
    def supported_metrics(self) -> List[str]:
        """Return the list of metric names this framework can compute."""
        raise NotImplementedError

    @abstractmethod
    def evaluate(
        self,
        rows: List[EvalRow],
        metrics: List[str],
        *,
        llm_model: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ) -> EvalScores:
        """Score the given rows on the requested metrics.

        Args:
            rows: Rows to evaluate (must already contain responses).
            metrics: Metric names to compute.
            llm_model: Optional LLM model identifier for judge-based metrics.
            embedding_model: Optional embedding model for context metrics.

        Returns:
            EvalScores with per-row and aggregate results.
        """
        raise NotImplementedError

    def validate_metrics(self, metrics: List[str]) -> List[str]:
        """Return the subset of requested metrics not supported by this framework."""
        supported = set(self.supported_metrics())
        return [m for m in metrics if m not in supported]
