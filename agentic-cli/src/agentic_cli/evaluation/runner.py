"""Evaluation runner for measuring agent performance."""

import asyncio
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from agentic_cli.evaluation.datasets import EvaluationDataset, EvaluationSample
from agentic_cli.evaluation.metrics import Metric, MetricsCalculator, get_metric


@dataclass
class SampleResult:
    """Result of evaluating a single sample."""
    sample_id: str
    input_text: str
    expected_output: str
    actual_output: str
    metric_scores: Dict[str, float] = field(default_factory=dict)
    latency_ms: float = 0.0
    tokens_used: int = 0
    passed: bool = True
    errors: List[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    """Results from a full evaluation run."""
    eval_id: str
    agent_name: str
    skill_name: Optional[str]
    dataset_id: str
    judge_type: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metrics_used: List[str] = field(default_factory=list)
    sample_results: List[SampleResult] = field(default_factory=list)
    summary_metrics: Dict[str, float] = field(default_factory=dict)
    passed_count: int = 0
    failed_count: int = 0
    total_samples: int = 0
    average_latency_ms: float = 0.0
    total_tokens: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "eval_id": self.eval_id,
            "agent_name": self.agent_name,
            "skill_name": self.skill_name,
            "dataset_id": self.dataset_id,
            "judge_type": self.judge_type,
            "timestamp": self.timestamp,
            "metrics_used": self.metrics_used,
            "sample_results": [asdict(r) for r in self.sample_results],
            "summary_metrics": self.summary_metrics,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "total_samples": self.total_samples,
            "average_latency_ms": self.average_latency_ms,
            "total_tokens": self.total_tokens,
        }


class EvaluationRunner:
    """Runs evaluations on agents using datasets and metrics."""

    def __init__(
        self,
        agent_fn: Callable,
        dataset: EvaluationDataset,
        metrics: List[str],
        eval_id: str,
        agent_name: str = "unknown",
        judge_type: str = "none",
        skill_name: Optional[str] = None,
    ):
        """Initialize evaluation runner.

        Args:
            agent_fn: Async function that takes input_text and returns output
            dataset: EvaluationDataset with test samples
            metrics: List of metric names to calculate
            eval_id: Unique evaluation ID
            agent_name: Name of the agent being evaluated
            judge_type: Type of LLM judge to use (vertex-ai, anthropic, openai, none)
            skill_name: Optional skill being tested
        """
        self.agent_fn = agent_fn
        self.dataset = dataset
        self.metrics = metrics
        self.eval_id = eval_id
        self.agent_name = agent_name
        self.judge_type = judge_type
        self.skill_name = skill_name
        self.judge = None

        # Initialize judge if needed
        if judge_type != "none":
            from agentic_cli.evaluation.llm_judges import get_judge

            try:
                self.judge = get_judge(judge_type)
                if not self.judge.is_available():
                    raise RuntimeError(f"Judge {judge_type} not available")
            except Exception as e:
                raise RuntimeError(f"Failed to initialize judge: {e}")

    async def run(self) -> EvaluationResult:
        """Run the full evaluation.

        Returns:
            EvaluationResult with all scores and metrics
        """
        result = EvaluationResult(
            eval_id=self.eval_id,
            agent_name=self.agent_name,
            skill_name=self.skill_name,
            dataset_id=self.dataset.id,
            judge_type=self.judge_type,
            metrics_used=self.metrics,
            total_samples=len(self.dataset.samples),
        )

        total_latency = 0.0
        total_tokens = 0

        # Run each sample
        for sample in self.dataset.samples:
            try:
                # Run agent
                start_time = time.time()
                actual_output = await self._run_agent(sample.input)
                latency_ms = (time.time() - start_time) * 1000

                # Calculate metrics
                metric_scores = await self._calculate_metrics(
                    sample.input,
                    sample.expected_output,
                    actual_output,
                )

                # Estimate tokens
                tokens = (
                    MetricsCalculator.calculate_token_count(sample.input)
                    + MetricsCalculator.calculate_token_count(actual_output)
                )

                # Create sample result
                sample_result = SampleResult(
                    sample_id=sample.sample_id or f"sample-{len(result.sample_results)}",
                    input_text=sample.input,
                    expected_output=sample.expected_output,
                    actual_output=actual_output,
                    metric_scores=metric_scores,
                    latency_ms=latency_ms,
                    tokens_used=tokens,
                    passed=True,
                )

                result.sample_results.append(sample_result)
                total_latency += latency_ms
                total_tokens += tokens
                result.passed_count += 1

            except Exception as e:
                result.failed_count += 1
                result.sample_results.append(
                    SampleResult(
                        sample_id=sample.sample_id or f"sample-{len(result.sample_results)}",
                        input_text=sample.input,
                        expected_output=sample.expected_output,
                        actual_output="",
                        passed=False,
                        errors=[str(e)],
                    )
                )

        # Calculate summary metrics
        if result.sample_results:
            result.average_latency_ms = total_latency / len(result.sample_results)
            result.total_tokens = total_tokens

            # Aggregate metric scores
            result.summary_metrics = self._aggregate_metrics(result.sample_results)

        return result

    async def _run_agent(self, input_text: str) -> str:
        """Run agent on input and return output."""
        if asyncio.iscoroutinefunction(self.agent_fn):
            return await self.agent_fn(input_text)
        else:
            return self.agent_fn(input_text)

    async def _calculate_metrics(
        self,
        input_text: str,
        expected_output: str,
        actual_output: str,
    ) -> Dict[str, float]:
        """Calculate all metrics for a sample."""
        scores = {}

        for metric_name in self.metrics:
            metric = get_metric(metric_name)
            if not metric:
                continue

            try:
                if metric_name == "accuracy":
                    score = MetricsCalculator.calculate_accuracy(
                        expected_output, actual_output
                    )
                elif metric_name == "bleu_score":
                    score = MetricsCalculator.calculate_bleu_score(
                        expected_output, actual_output
                    )
                elif metric_name == "f1_score":
                    score = MetricsCalculator.calculate_f1_score(
                        expected_output, actual_output
                    )
                elif metric_name in ("helpfulness", "clarity", "relevance", "safety"):
                    # Use LLM judge for qualitative metrics
                    if self.judge:
                        score = await self.judge.evaluate(
                            input_text,
                            expected_output,
                            actual_output,
                            metric_name,
                            metric.description,
                        )
                    else:
                        score = 3.0  # Default neutral score
                else:
                    score = 0.5  # Default score for unknown metrics

                scores[metric_name] = float(score)

            except Exception as e:
                # Use default score on error
                scores[metric_name] = 0.5

        return scores

    @staticmethod
    def _aggregate_metrics(sample_results: List[SampleResult]) -> Dict[str, float]:
        """Aggregate metric scores across all samples."""
        if not sample_results:
            return {}

        aggregated = {}

        # Find all metric names
        all_metrics = set()
        for result in sample_results:
            all_metrics.update(result.metric_scores.keys())

        # Calculate averages
        for metric_name in all_metrics:
            scores = [
                r.metric_scores[metric_name]
                for r in sample_results
                if metric_name in r.metric_scores
            ]
            if scores:
                aggregated[metric_name] = sum(scores) / len(scores)

        return aggregated


class SkillImpactEvaluator:
    """Evaluates the impact of a skill on agent performance."""

    def __init__(
        self,
        dataset: EvaluationDataset,
        metrics: List[str],
        judge_type: str = "anthropic",
    ):
        """Initialize skill impact evaluator.

        Args:
            dataset: EvaluationDataset to use
            metrics: List of metric names
            judge_type: Type of LLM judge to use
        """
        self.dataset = dataset
        self.metrics = metrics
        self.judge_type = judge_type

    async def evaluate_impact(
        self,
        agent_fn: Callable,
        agent_name: str,
        skill_name: str,
        baseline_agent_fn: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Evaluate the impact of a skill.

        Compares agent performance with and without skill.

        Args:
            agent_fn: Agent function (with skill enabled)
            agent_name: Name of the agent
            skill_name: Name of the skill being tested
            baseline_agent_fn: Optional agent without skill (defaults to agent_fn)

        Returns:
            Dict with baseline results, impact results, and improvement metrics
        """
        import uuid

        # Use baseline agent without skill
        if not baseline_agent_fn:
            baseline_agent_fn = agent_fn

        # Run baseline evaluation
        baseline_runner = EvaluationRunner(
            agent_fn=baseline_agent_fn,
            dataset=self.dataset,
            metrics=self.metrics,
            eval_id=f"baseline-{uuid.uuid4().hex[:8]}",
            agent_name=agent_name,
            judge_type=self.judge_type,
        )
        baseline_result = await baseline_runner.run()

        # Run evaluation with skill
        impact_runner = EvaluationRunner(
            agent_fn=agent_fn,
            dataset=self.dataset,
            metrics=self.metrics,
            eval_id=f"impact-{uuid.uuid4().hex[:8]}",
            agent_name=agent_name,
            judge_type=self.judge_type,
            skill_name=skill_name,
        )
        impact_result = await impact_runner.run()

        # Calculate deltas
        deltas = self._calculate_deltas(
            baseline_result.summary_metrics,
            impact_result.summary_metrics,
        )

        return {
            "baseline": baseline_result.to_dict(),
            "with_skill": impact_result.to_dict(),
            "deltas": deltas,
            "skill_effectiveness": self._calculate_effectiveness(deltas),
        }

    @staticmethod
    def _calculate_deltas(
        baseline_metrics: Dict[str, float],
        impact_metrics: Dict[str, float],
    ) -> Dict[str, float]:
        """Calculate metric deltas."""
        deltas = {}

        for metric_name, baseline_score in baseline_metrics.items():
            if metric_name not in impact_metrics:
                continue

            impact_score = impact_metrics[metric_name]
            metric = get_metric(metric_name)

            if not metric:
                continue

            # Calculate delta (positive = improvement)
            if metric.lower_is_better:
                # For metrics where lower is better, negative delta is improvement
                delta = baseline_score - impact_score
            else:
                # For metrics where higher is better, positive delta is improvement
                delta = impact_score - baseline_score

            deltas[metric_name] = delta

        return deltas

    @staticmethod
    def _calculate_effectiveness(deltas: Dict[str, float]) -> float:
        """Calculate overall skill effectiveness score (0-10)."""
        if not deltas:
            return 0.0

        # Weight each delta
        weighted_sum = 0.0
        total_weight = 0.0

        for metric_name, delta in deltas.items():
            metric = get_metric(metric_name)
            if not metric:
                continue

            # Normalize delta to -1 to +1 range
            normalized_delta = max(-1.0, min(1.0, delta))

            # Convert to 0-10 scale
            weighted_sum += (normalized_delta + 1) * 5 * metric.weight
            total_weight += metric.weight

        if total_weight == 0:
            return 0.0

        return weighted_sum / total_weight
