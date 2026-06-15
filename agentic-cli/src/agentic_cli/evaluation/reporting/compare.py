"""Cross-agent and cross-version comparison of evaluation runs."""

from dataclasses import dataclass, field
from typing import Dict, List

from agentic_cli.evaluation.results import EvalRunResult


@dataclass
class ComparisonRow:
    """One metric's scores across the compared runs."""

    metric: str
    scores: Dict[str, float] = field(default_factory=dict)  # label -> raw score
    best_label: str = ""


@dataclass
class Comparison:
    """Result of comparing multiple evaluation runs."""

    labels: List[str] = field(default_factory=list)          # column labels (agent/version)
    rows: List[ComparisonRow] = field(default_factory=list)  # one per metric
    overall: Dict[str, float] = field(default_factory=dict)  # label -> normalized overall (0-1)
    ranking: List[str] = field(default_factory=list)         # labels best -> worst
    runs: List[EvalRunResult] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """JSON-serializable representation."""
        return {
            "labels": self.labels,
            "overall": self.overall,
            "ranking": self.ranking,
            "rows": [
                {"metric": r.metric, "scores": r.scores, "best_label": r.best_label}
                for r in self.rows
            ],
        }


def _label_for(run: EvalRunResult, by_version: bool) -> str:
    """Build a stable column label for a run."""
    if by_version:
        ver = f"v{run.dataset_version}" if run.dataset_version is not None else run.eval_id[:8]
        return f"{run.agent}@{ver}"
    return run.agent or run.eval_id[:8]


def compare_runs(runs: List[EvalRunResult], by_version: bool = False) -> Comparison:
    """Compare evaluation runs across agents (or versions).

    Args:
        runs: Runs to compare (typically same eval config, different agents).
        by_version: If True, label columns by agent@version to compare versions.

    Returns:
        A populated :class:`Comparison`.
    """
    comparison = Comparison(runs=list(runs))
    if not runs:
        return comparison

    labels = [_label_for(r, by_version) for r in runs]
    # De-duplicate labels by suffixing an index when needed.
    seen: Dict[str, int] = {}
    unique_labels: List[str] = []
    for label in labels:
        if label in seen:
            seen[label] += 1
            unique_labels.append(f"{label}#{seen[label]}")
        else:
            seen[label] = 0
            unique_labels.append(label)
    comparison.labels = unique_labels

    label_to_run = dict(zip(unique_labels, runs))

    # Collect the union of all metrics across runs (preserve order of appearance).
    metric_order: List[str] = []
    for run in runs:
        for m in run.metrics:
            if m not in metric_order:
                metric_order.append(m)
        for m in run.aggregate:
            if m not in metric_order:
                metric_order.append(m)

    # Per-metric rows. "Best" uses normalized (higher-is-better) scores.
    for metric in metric_order:
        row = ComparisonRow(metric=metric)
        best_label, best_norm = "", float("-inf")
        for label, run in label_to_run.items():
            if metric in run.aggregate:
                row.scores[label] = run.aggregate[metric]
                norm = run.normalized_aggregate().get(metric, run.aggregate[metric])
                if norm > best_norm:
                    best_norm, best_label = norm, label
        row.best_label = best_label
        comparison.rows.append(row)

    # Overall normalized score per label + ranking.
    for label, run in label_to_run.items():
        comparison.overall[label] = run.overall_score()
    comparison.ranking = sorted(
        comparison.overall, key=lambda lbl: comparison.overall[lbl], reverse=True
    )

    return comparison
