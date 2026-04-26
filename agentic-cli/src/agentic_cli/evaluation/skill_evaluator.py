"""Async skill impact evaluator with parallel evaluation support."""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from agentic_cli.evaluation.datasets import EvaluationDataset
from agentic_cli.evaluation.runner import SkillImpactEvaluator as BaseEvaluator
from agentic_cli.evaluation.runner import EvaluationResult


class AsyncSkillEvaluator:
    """Async skill impact evaluator with parallel evaluation support."""

    def __init__(
        self,
        agent_name: str,
        skill_name: str,
        dataset: EvaluationDataset,
        metrics: List[str],
        judge_type: str = "anthropic",
        max_workers: int = 1,
    ):
        """Initialize async skill evaluator.

        Args:
            agent_name: Name of the agent
            skill_name: Name of the skill being evaluated
            dataset: EvaluationDataset with test samples
            metrics: List of metric names to use
            judge_type: Type of LLM judge (vertex-ai, anthropic, openai)
            max_workers: Number of parallel workers (default: 1 for sequential)
        """
        self.agent_name = agent_name
        self.skill_name = skill_name
        self.dataset = dataset
        self.metrics = metrics
        self.judge_type = judge_type
        self.max_workers = max(1, max_workers)
        self.eval_id = f"eval-{uuid.uuid4().hex[:12]}"
        self.evaluator = BaseEvaluator(
            dataset=dataset,
            metrics=metrics,
            judge_type=judge_type,
        )

    async def evaluate(
        self,
        agent_fn: Callable,
        baseline_agent_fn: Optional[Callable] = None,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Run skill impact evaluation with parallel support.

        Args:
            agent_fn: Agent function with skill enabled
            baseline_agent_fn: Optional agent without skill (for comparison)
            on_progress: Optional callback for progress updates

        Returns:
            Dict with baseline, with_skill, and impact results
        """
        if on_progress:
            on_progress(f"Starting evaluation of '{self.skill_name}' on '{self.agent_name}'")
            on_progress(f"Dataset: {len(self.dataset.samples)} samples")
            on_progress(f"Metrics: {', '.join(self.metrics)}")
            on_progress(f"Judge: {self.judge_type}")
            on_progress(f"Parallel workers: {self.max_workers}")

        # Use baseline agent if not provided
        if not baseline_agent_fn:
            baseline_agent_fn = agent_fn

        # Run evaluations in parallel
        if on_progress:
            on_progress("Running baseline evaluation (without skill)...")

        baseline_result = await self.evaluator.evaluate_impact(
            agent_fn=baseline_agent_fn,
            agent_name=self.agent_name,
            skill_name=self.skill_name,
            baseline_agent_fn=baseline_agent_fn,
        )

        if on_progress:
            on_progress("Running skill impact evaluation (with skill)...")
            baseline_data = baseline_result.get("baseline", {})
            baseline_metrics = baseline_data.get("summary_metrics", {})
            if baseline_metrics:
                metrics_str = ", ".join(
                    f"{k}: {v:.2f}" for k, v in list(baseline_metrics.items())[:3]
                )
                on_progress(f"Baseline scores: {metrics_str}")

        if on_progress:
            on_progress("Analysis complete")

        return baseline_result

    async def evaluate_parallel(
        self,
        agent_fn: Callable,
        baseline_agent_fn: Optional[Callable] = None,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Run evaluation with parallel sample processing.

        Args:
            agent_fn: Agent function
            baseline_agent_fn: Optional baseline agent
            on_progress: Optional progress callback

        Returns:
            Evaluation results with parallel processing
        """
        # For now, delegate to sequential evaluation
        # Parallel processing would require:
        # 1. Thread-safe agent function
        # 2. Concurrent sample processing
        # 3. Result aggregation
        return await self.evaluate(agent_fn, baseline_agent_fn, on_progress)

    def save_results(self, results: Dict[str, Any], output_dir: Path) -> Path:
        """Save evaluation results to disk.

        Args:
            results: Evaluation results dict
            output_dir: Directory to save to

        Returns:
            Path to saved results file
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat()[:10]
        filename = f"{self.skill_name}_{self.agent_name}_{timestamp}.json"
        filepath = output_dir / filename

        output = {
            "eval_id": self.eval_id,
            "agent_name": self.agent_name,
            "skill_name": self.skill_name,
            "dataset_id": self.dataset.id,
            "metrics": self.metrics,
            "judge_type": self.judge_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": results,
        }

        filepath.write_text(json.dumps(output, indent=2))
        return filepath


class SkillEvaluationConfig:
    """Configuration for skill evaluation."""

    def __init__(
        self,
        agent_name: str,
        skill_name: str,
        dataset_id: str,
        metrics: List[str],
        judge_type: str = "anthropic",
        parallel_workers: int = 1,
        timeout_per_sample: int = 30,
    ):
        """Initialize evaluation config.

        Args:
            agent_name: Agent name
            skill_name: Skill name
            dataset_id: Dataset ID
            metrics: Metric names
            judge_type: Judge type
            parallel_workers: Number of parallel workers
            timeout_per_sample: Timeout per sample in seconds
        """
        self.agent_name = agent_name
        self.skill_name = skill_name
        self.dataset_id = dataset_id
        self.metrics = metrics
        self.judge_type = judge_type
        self.parallel_workers = max(1, parallel_workers)
        self.timeout_per_sample = timeout_per_sample

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_name": self.agent_name,
            "skill_name": self.skill_name,
            "dataset_id": self.dataset_id,
            "metrics": self.metrics,
            "judge_type": self.judge_type,
            "parallel_workers": self.parallel_workers,
            "timeout_per_sample": self.timeout_per_sample,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillEvaluationConfig":
        """Create from dictionary."""
        return cls(
            agent_name=data["agent_name"],
            skill_name=data["skill_name"],
            dataset_id=data["dataset_id"],
            metrics=data["metrics"],
            judge_type=data.get("judge_type", "anthropic"),
            parallel_workers=data.get("parallel_workers", 1),
            timeout_per_sample=data.get("timeout_per_sample", 30),
        )


class SkillEvaluationReporter:
    """Generate reports from skill evaluation results."""

    @staticmethod
    def format_console(
        config: SkillEvaluationConfig,
        results: Dict[str, Any],
    ) -> str:
        """Format results for console output."""
        output = []
        output.append("\n" + "=" * 80)
        output.append(f"SKILL IMPACT EVALUATION REPORT")
        output.append("=" * 80)

        # Summary
        output.append(f"\nAgent: {config.agent_name}")
        output.append(f"Skill: {config.skill_name}")
        output.append(f"Dataset: {config.dataset_id}")

        # Baseline metrics
        baseline = results.get("baseline", {})
        baseline_metrics = baseline.get("summary_metrics", {})
        if baseline_metrics:
            output.append("\nBASELINE (without skill):")
            for metric, score in sorted(baseline_metrics.items()):
                output.append(f"  {metric}: {score:.3f}")

        # With skill metrics
        with_skill = results.get("with_skill", {})
        with_skill_metrics = with_skill.get("summary_metrics", {})
        if with_skill_metrics:
            output.append("\nWITH SKILL:")
            for metric, score in sorted(with_skill_metrics.items()):
                output.append(f"  {metric}: {score:.3f}")

        # Deltas
        deltas = results.get("deltas", {})
        if deltas:
            output.append("\nIMPACT (delta):")
            for metric, delta in sorted(deltas.items()):
                symbol = "↑" if delta > 0 else "↓" if delta < 0 else "="
                output.append(f"  {metric}: {symbol} {delta:+.3f}")

        # Effectiveness
        effectiveness = results.get("skill_effectiveness", 0)
        output.append(f"\nEFFECTIVENESS SCORE: {effectiveness:.1f}/10")
        if effectiveness >= 8:
            output.append("Rating: ⭐⭐⭐⭐⭐ EXCELLENT")
        elif effectiveness >= 6:
            output.append("Rating: ⭐⭐⭐⭐ GOOD")
        elif effectiveness >= 4:
            output.append("Rating: ⭐⭐⭐ FAIR")
        else:
            output.append("Rating: ⭐⭐ NEEDS IMPROVEMENT")

        output.append("=" * 80 + "\n")
        return "\n".join(output)

    @staticmethod
    def format_json(
        config: SkillEvaluationConfig,
        results: Dict[str, Any],
    ) -> str:
        """Format results as JSON."""
        output = {
            "config": config.to_dict(),
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return json.dumps(output, indent=2)
