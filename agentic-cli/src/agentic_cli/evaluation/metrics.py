"""Metric definitions and calculations for agent evaluation."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional


class MetricType(str, Enum):
    """Types of metrics."""
    QUANTITATIVE = "quantitative"  # Numeric values (0-1 or percentage)
    QUALITATIVE = "qualitative"    # LLM-judged ratings (1-5)
    CATEGORICAL = "categorical"    # Discrete categories
    BOOLEAN = "boolean"            # Pass/fail


@dataclass
class Metric:
    """Definition of an evaluation metric."""
    name: str
    description: str
    metric_type: MetricType
    unit: str = ""
    lower_is_better: bool = False
    threshold: Optional[float] = None
    weight: float = 1.0
    calculation: Optional[Callable] = None

    def __post_init__(self):
        """Validate metric configuration."""
        if self.weight <= 0:
            raise ValueError(f"Metric weight must be positive, got {self.weight}")


# Built-in metrics
BUILT_IN_METRICS = {
    # Quantitative metrics
    "accuracy": Metric(
        name="accuracy",
        description="Exact match accuracy between expected and actual output",
        metric_type=MetricType.QUANTITATIVE,
        unit="%",
        lower_is_better=False,
        threshold=0.85,
        weight=2.0,
    ),
    "f1_score": Metric(
        name="f1_score",
        description="F1 score (precision/recall harmonic mean)",
        metric_type=MetricType.QUANTITATIVE,
        unit="score",
        lower_is_better=False,
        threshold=0.80,
        weight=1.5,
    ),
    "bleu_score": Metric(
        name="bleu_score",
        description="BLEU score for text similarity",
        metric_type=MetricType.QUANTITATIVE,
        unit="score",
        lower_is_better=False,
        threshold=0.70,
        weight=1.5,
    ),
    "latency_ms": Metric(
        name="latency_ms",
        description="Response time in milliseconds",
        metric_type=MetricType.QUANTITATIVE,
        unit="ms",
        lower_is_better=True,
        threshold=5000,
        weight=1.0,
    ),
    "token_usage": Metric(
        name="token_usage",
        description="Average tokens used per request",
        metric_type=MetricType.QUANTITATIVE,
        unit="tokens",
        lower_is_better=True,
        threshold=2000,
        weight=0.5,
    ),
    "cost_usd": Metric(
        name="cost_usd",
        description="Average cost per request in USD",
        metric_type=MetricType.QUANTITATIVE,
        unit="$",
        lower_is_better=True,
        threshold=0.10,
        weight=0.5,
    ),
    # Qualitative metrics (LLM-judged)
    "helpfulness": Metric(
        name="helpfulness",
        description="How helpful is the response (1-5 scale)",
        metric_type=MetricType.QUALITATIVE,
        unit="score",
        lower_is_better=False,
        threshold=4.0,
        weight=2.0,
    ),
    "clarity": Metric(
        name="clarity",
        description="How clear and understandable is the response (1-5 scale)",
        metric_type=MetricType.QUALITATIVE,
        unit="score",
        lower_is_better=False,
        threshold=4.0,
        weight=1.5,
    ),
    "relevance": Metric(
        name="relevance",
        description="How relevant is the response to the question (1-5 scale)",
        metric_type=MetricType.QUALITATIVE,
        unit="score",
        lower_is_better=False,
        threshold=4.0,
        weight=2.0,
    ),
    "safety": Metric(
        name="safety",
        description="Is the response safe and non-harmful (1-5 scale)",
        metric_type=MetricType.QUALITATIVE,
        unit="score",
        lower_is_better=False,
        threshold=4.5,
        weight=1.5,
    ),
    # Boolean/categorical metrics
    "contains_hallucination": Metric(
        name="contains_hallucination",
        description="Whether response contains factually incorrect information",
        metric_type=MetricType.BOOLEAN,
        lower_is_better=True,
        weight=2.0,
    ),
    "is_complete": Metric(
        name="is_complete",
        description="Whether response fully addresses the question",
        metric_type=MetricType.BOOLEAN,
        lower_is_better=False,
        weight=1.5,
    ),
}


def get_metric(metric_name: str) -> Optional[Metric]:
    """Get a built-in metric by name."""
    return BUILT_IN_METRICS.get(metric_name)


def get_all_metrics() -> dict[str, Metric]:
    """Get all built-in metrics."""
    return BUILT_IN_METRICS.copy()


def calculate_composite_score(
    metric_scores: dict[str, float],
    metrics: dict[str, Metric],
) -> float:
    """Calculate weighted composite score from individual metrics.

    Args:
        metric_scores: Dict of metric_name -> score (0-1 or 0-5)
        metrics: Dict of metric_name -> Metric definition

    Returns:
        Weighted composite score (0-1)
    """
    weighted_sum = 0.0
    total_weight = 0.0

    for metric_name, score in metric_scores.items():
        metric = metrics.get(metric_name)
        if not metric:
            continue

        # Normalize score to 0-1 range based on metric type
        if metric.metric_type == MetricType.QUALITATIVE:
            # Scale 1-5 to 0-1
            normalized = max(0, min(1.0, (score - 1) / 4))
        elif metric.metric_type == MetricType.BOOLEAN:
            # Already 0 or 1
            normalized = float(score)
        else:
            # Assume 0-1 range already
            normalized = max(0, min(1.0, score))

        weighted_sum += normalized * metric.weight
        total_weight += metric.weight

    if total_weight == 0:
        return 0.0

    return weighted_sum / total_weight


class MetricsCalculator:
    """Calculates metrics from agent responses."""

    @staticmethod
    def calculate_accuracy(expected: str, actual: str) -> float:
        """Calculate exact match accuracy (0 or 1)."""
        return 1.0 if expected.strip() == actual.strip() else 0.0

    @staticmethod
    def calculate_token_count(text: str) -> int:
        """Estimate token count (rough approximation)."""
        # Rough estimate: ~4 characters per token
        return len(text) // 4

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for comparison."""
        return " ".join(text.lower().split())

    @staticmethod
    def calculate_bleu_score(expected: str, actual: str) -> float:
        """Calculate simplified BLEU score (0-1).

        Note: This is a simplified calculation. For production,
        use nltk.translate.bleu_score or similar.
        """
        expected_words = set(MetricsCalculator.normalize_text(expected).split())
        actual_words = set(MetricsCalculator.normalize_text(actual).split())

        if not expected_words:
            return 1.0 if not actual_words else 0.0

        intersection = expected_words & actual_words
        return len(intersection) / len(expected_words)

    @staticmethod
    def calculate_f1_score(expected: str, actual: str) -> float:
        """Calculate simplified F1 score (0-1).

        Note: This is a simplified calculation based on word overlap.
        """
        expected_words = set(MetricsCalculator.normalize_text(expected).split())
        actual_words = set(MetricsCalculator.normalize_text(actual).split())

        if not expected_words and not actual_words:
            return 1.0

        if not expected_words or not actual_words:
            return 0.0

        intersection = expected_words & actual_words
        precision = len(intersection) / len(actual_words) if actual_words else 0
        recall = len(intersection) / len(expected_words) if expected_words else 0

        if precision + recall == 0:
            return 0.0

        return 2 * (precision * recall) / (precision + recall)
