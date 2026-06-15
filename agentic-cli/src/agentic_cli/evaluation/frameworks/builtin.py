"""Built-in evaluation framework.

Computes scores using the CLI's existing metrics (`metrics.py`) and LLM judges
(`llm_judges.py`). Requires no extra dependencies. Quantitative metrics are
computed locally; qualitative metrics (1-5) use an LLM judge when available and
fall back to a neutral score otherwise.
"""

import asyncio
import logging
from typing import Dict, List, Optional

from agentic_cli.evaluation.frameworks.base import EvalFramework, EvalRow, EvalScores
from agentic_cli.evaluation.metrics import (
    BUILT_IN_METRICS,
    MetricsCalculator,
    MetricType,
    get_metric,
)

logger = logging.getLogger(__name__)

# Qualitative metrics scored by an LLM judge (1-5 scale).
_JUDGE_METRICS = {"helpfulness", "clarity", "relevance", "safety"}
# Local quantitative scorers (0-1 scale).
_LOCAL_SCORERS = {"accuracy", "bleu_score", "f1_score"}


class BuiltinFramework(EvalFramework):
    """Framework backed by the CLI's native metrics and judges."""

    name = "builtin"

    def __init__(self, judge_type: str = "none", custom_metrics: Optional[Dict[str, str]] = None):
        """Initialize the builtin framework.

        Args:
            judge_type: LLM judge to use for qualitative metrics
                (vertex-ai, anthropic, openai, or none).
            custom_metrics: Optional mapping of custom metric name -> scoring
                prompt (criteria). Scored on a 1-5 scale via the LLM judge,
                with a neutral fallback when no judge is available.
        """
        self.judge_type = judge_type
        self.custom_metrics = dict(custom_metrics or {})
        self._judge = None
        if judge_type and judge_type != "none":
            from agentic_cli.evaluation.llm_judges import get_judge

            try:
                judge = get_judge(judge_type)
                if judge.is_available():
                    self._judge = judge
                else:
                    logger.warning(
                        f"Judge '{judge_type}' is not available; qualitative "
                        "metrics will use a neutral fallback score."
                    )
            except Exception as e:  # pragma: no cover - defensive
                logger.warning(f"Failed to init judge '{judge_type}': {e}")

    def supported_metrics(self) -> List[str]:
        """All built-in metric names plus any registered custom metrics."""
        return list(BUILT_IN_METRICS.keys()) + list(self.custom_metrics.keys())

    def evaluate(
        self,
        rows: List[EvalRow],
        metrics: List[str],
        *,
        llm_model: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ) -> EvalScores:
        """Score rows using local calculators and (optionally) an LLM judge."""
        scores = EvalScores(framework=self.name)

        for row in rows:
            row_scores = asyncio.run(self._score_row(row, metrics))
            scores.per_row.append(row_scores)

        # Aggregate (mean) per metric and record ranges.
        scores.aggregate = self._aggregate(scores.per_row)
        scores.metric_ranges = self._ranges(metrics)
        return scores

    async def _score_row(self, row: EvalRow, metrics: List[str]) -> Dict[str, float]:
        """Compute all requested metric scores for a single row."""
        result: Dict[str, float] = {}
        for metric_name in metrics:
            try:
                # Custom (prompt-based) metric.
                if metric_name in self.custom_metrics:
                    result[metric_name] = await self._score_custom(metric_name, row)
                    continue
                metric = get_metric(metric_name)
                if not metric:
                    continue
                result[metric_name] = await self._score_metric(metric_name, metric, row)
            except Exception as e:  # pragma: no cover - defensive
                logger.debug(f"Metric '{metric_name}' failed: {e}")
                result[metric_name] = 0.0
        return result

    async def _score_custom(self, name: str, row: EvalRow) -> float:
        """Score a custom prompt-based metric via the LLM judge (1-5)."""
        if self._judge:
            return float(
                await self._judge.evaluate(
                    row.input_text,
                    row.reference,
                    row.response,
                    name,
                    self.custom_metrics[name],
                )
            )
        return 3.0  # neutral fallback on 1-5 scale

    async def _score_metric(self, name, metric, row: EvalRow) -> float:
        """Score one metric for one row."""
        if name == "accuracy":
            return MetricsCalculator.calculate_accuracy(row.reference, row.response)
        if name == "bleu_score":
            return MetricsCalculator.calculate_bleu_score(row.reference, row.response)
        if name == "f1_score":
            return MetricsCalculator.calculate_f1_score(row.reference, row.response)
        if name in _JUDGE_METRICS:
            if self._judge:
                return float(
                    await self._judge.evaluate(
                        row.input_text,
                        row.reference,
                        row.response,
                        name,
                        metric.description,
                    )
                )
            return 3.0  # neutral fallback on 1-5 scale
        # Boolean / unknown metrics: neutral default.
        if metric.metric_type == MetricType.BOOLEAN:
            return 0.0
        return 0.5

    @staticmethod
    def _aggregate(per_row: List[Dict[str, float]]) -> Dict[str, float]:
        """Mean of each metric across rows."""
        if not per_row:
            return {}
        names: set = set()
        for r in per_row:
            names.update(r.keys())
        agg: Dict[str, float] = {}
        for name in names:
            vals = [r[name] for r in per_row if name in r]
            if vals:
                agg[name] = sum(vals) / len(vals)
        return agg

    def _ranges(self, metrics: List[str]) -> Dict[str, list]:
        """Score range per metric so consumers can normalize across frameworks."""
        ranges: Dict[str, list] = {}
        for name in metrics:
            if name in self.custom_metrics:
                ranges[name] = [1.0, 5.0]
                continue
            metric = get_metric(name)
            if not metric:
                continue
            if metric.metric_type == MetricType.QUALITATIVE:
                ranges[name] = [1.0, 5.0]
            else:
                ranges[name] = [0.0, 1.0]
        return ranges
