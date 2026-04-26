"""Tests for async skill evaluator."""

import asyncio
import json
import tempfile
from pathlib import Path

import pytest

from agentic_cli.evaluation.agent_adapters import AgentAdapter, MockAgents
from agentic_cli.evaluation.datasets import DatasetManager, EvaluationSample
from agentic_cli.evaluation.skill_evaluator import (
    AsyncSkillEvaluator,
    SkillEvaluationConfig,
    SkillEvaluationReporter,
)


@pytest.fixture
def temp_datasets_dir():
    """Create temporary datasets directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_dataset(temp_datasets_dir):
    """Create a sample dataset for testing."""
    manager = DatasetManager(temp_datasets_dir)
    dataset = manager.create_dataset(
        dataset_id="test-qa",
        name="Test QA",
        description="Test dataset",
        tags=["test"],
    )

    # Add samples
    dataset.add_sample(
        EvaluationSample(
            input="What is Python?",
            expected_output="Python is a programming language.",
        )
    )
    dataset.add_sample(
        EvaluationSample(
            input="What is AI?",
            expected_output="AI stands for Artificial Intelligence.",
        )
    )
    dataset.add_sample(
        EvaluationSample(
            input="What is machine learning?",
            expected_output="Machine learning is a subset of AI.",
        )
    )

    manager.save_dataset(dataset)
    return dataset


@pytest.mark.asyncio
async def test_async_skill_evaluator_creation(sample_dataset):
    """Test creating an async skill evaluator."""
    evaluator = AsyncSkillEvaluator(
        agent_name="test-agent",
        skill_name="test-skill",
        dataset=sample_dataset,
        metrics=["accuracy", "bleu_score"],
        judge_type="anthropic",
        max_workers=1,
    )

    assert evaluator.agent_name == "test-agent"
    assert evaluator.skill_name == "test-skill"
    assert evaluator.max_workers == 1
    assert len(sample_dataset.samples) == 3


@pytest.mark.asyncio
async def test_async_skill_evaluator_with_mock_agent(sample_dataset):
    """Test evaluator with mock agent."""
    evaluator = AsyncSkillEvaluator(
        agent_name="test-agent",
        skill_name="test-skill",
        dataset=sample_dataset,
        metrics=["accuracy"],
        judge_type="anthropic",
    )

    # Use mock agent
    agent_fn = MockAgents.get_agent("simple")

    # Mock progress callback
    progress_messages = []

    def on_progress(msg: str) -> None:
        progress_messages.append(msg)

    # Run evaluation
    results = await evaluator.evaluate(
        agent_fn=agent_fn,
        baseline_agent_fn=agent_fn,
        on_progress=on_progress,
    )

    # Check results structure
    assert "baseline" in results
    assert "with_skill" in results
    assert "deltas" in results
    assert "skill_effectiveness" in results

    # Check progress messages
    assert len(progress_messages) > 0


@pytest.mark.asyncio
async def test_agent_adapter_sync_to_async():
    """Test wrapping sync agent to async."""

    def sync_agent(input_text: str) -> str:
        return f"Response to: {input_text}"

    async_agent = AgentAdapter.wrap_sync(sync_agent)

    result = await async_agent("test input")
    assert "test input" in result


@pytest.mark.asyncio
async def test_agent_adapter_ensure_async():
    """Test ensure_async with sync and async functions."""

    def sync_fn(text: str) -> str:
        return text.upper()

    async def async_fn(text: str) -> str:
        return text.lower()

    # Sync function should be wrapped
    wrapped_sync = AgentAdapter.ensure_async(sync_fn)
    assert asyncio.iscoroutinefunction(wrapped_sync)

    # Async function should be returned as-is
    wrapped_async = AgentAdapter.ensure_async(async_fn)
    assert wrapped_async is async_fn


@pytest.mark.asyncio
async def test_mock_agents():
    """Test all mock agent implementations."""

    # Test simple echo
    result = await MockAgents.simple_echo("test")
    assert result == "test"

    # Test QA agent
    qa_result = await MockAgents.simple_qa("What is Python?")
    assert "Python" in qa_result or "programming" in qa_result.lower()

    # Test helpful agent
    helpful_result = await MockAgents.helpful_agent("What is Python?")
    assert len(helpful_result) > 0


def test_skill_evaluation_config():
    """Test skill evaluation config."""
    config = SkillEvaluationConfig(
        agent_name="test-agent",
        skill_name="test-skill",
        dataset_id="test-dataset",
        metrics=["accuracy", "helpfulness"],
        judge_type="anthropic",
        parallel_workers=4,
    )

    # Test to_dict
    config_dict = config.to_dict()
    assert config_dict["agent_name"] == "test-agent"
    assert config_dict["skill_name"] == "test-skill"
    assert config_dict["parallel_workers"] == 4

    # Test from_dict
    restored = SkillEvaluationConfig.from_dict(config_dict)
    assert restored.agent_name == config.agent_name
    assert restored.parallel_workers == config.parallel_workers


def test_skill_evaluation_reporter_console():
    """Test console report formatting."""
    config = SkillEvaluationConfig(
        agent_name="test-agent",
        skill_name="test-skill",
        dataset_id="test-dataset",
        metrics=["accuracy"],
    )

    results = {
        "baseline": {"summary_metrics": {"accuracy": 0.8}},
        "with_skill": {"summary_metrics": {"accuracy": 0.9}},
        "deltas": {"accuracy": 0.1},
        "skill_effectiveness": 7.5,
    }

    report = SkillEvaluationReporter.format_console(config, results)

    assert "test-agent" in report
    assert "test-skill" in report
    assert "accuracy" in report
    assert "7.5" in report


def test_skill_evaluation_reporter_json():
    """Test JSON report formatting."""
    config = SkillEvaluationConfig(
        agent_name="test-agent",
        skill_name="test-skill",
        dataset_id="test-dataset",
        metrics=["accuracy"],
    )

    results = {
        "baseline": {"summary_metrics": {"accuracy": 0.8}},
        "with_skill": {"summary_metrics": {"accuracy": 0.9}},
        "deltas": {"accuracy": 0.1},
        "skill_effectiveness": 7.5,
    }

    json_report = SkillEvaluationReporter.format_json(config, results)

    # Verify it's valid JSON
    parsed = json.loads(json_report)
    assert parsed["config"]["agent_name"] == "test-agent"
    assert parsed["results"]["skill_effectiveness"] == 7.5


@pytest.mark.asyncio
async def test_parallel_workers_setting(sample_dataset):
    """Test parallel workers setting."""
    evaluator = AsyncSkillEvaluator(
        agent_name="test-agent",
        skill_name="test-skill",
        dataset=sample_dataset,
        metrics=["accuracy"],
        max_workers=4,
    )

    assert evaluator.max_workers == 4


def test_save_results(sample_dataset):
    """Test saving evaluation results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        evaluator = AsyncSkillEvaluator(
            agent_name="test-agent",
            skill_name="test-skill",
            dataset=sample_dataset,
            metrics=["accuracy"],
        )

        results = {
            "baseline": {"summary_metrics": {"accuracy": 0.8}},
            "with_skill": {"summary_metrics": {"accuracy": 0.9}},
            "deltas": {"accuracy": 0.1},
            "skill_effectiveness": 7.5,
        }

        output_dir = Path(tmpdir)
        saved_path = evaluator.save_results(results, output_dir)

        # Verify file was created
        assert saved_path.exists()
        assert saved_path.suffix == ".json"

        # Verify contents
        content = json.loads(saved_path.read_text())
        assert content["agent_name"] == "test-agent"
        assert content["skill_name"] == "test-skill"
