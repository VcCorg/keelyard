"""Tests for Phase 1 of the agent evaluation feature.

Covers: framework abstraction + builtin adapter, evaluation config manager,
CSV dataset versioning/register, and agent response collection.
"""

import tempfile
from pathlib import Path

import pytest

from agentic_cli.evaluation.frameworks import (
    EvalRow,
    BuiltinFramework,
    get_framework,
    list_frameworks,
)
from agentic_cli.evaluation.eval_config import EvaluationConfig, EvalConfigManager
from agentic_cli.evaluation.csv_dataset import CsvRow, CsvDatasetManager
from agentic_cli.evaluation.agent_runner import resolve_agent, AgentResponseCollector


# ---------------------------------------------------------------------------
# Framework registry + builtin framework
# ---------------------------------------------------------------------------

def test_list_frameworks_includes_builtin_and_ragas():
    fw = list_frameworks()
    assert "builtin" in fw
    assert "ragas" in fw


def test_get_framework_builtin():
    fw = get_framework("builtin")
    assert isinstance(fw, BuiltinFramework)
    assert fw.name == "builtin"


def test_get_framework_unknown_raises():
    with pytest.raises(ValueError):
        get_framework("does-not-exist")


def test_builtin_supported_metrics():
    fw = get_framework("builtin")
    metrics = fw.supported_metrics()
    assert "accuracy" in metrics
    assert "f1_score" in metrics
    assert "helpfulness" in metrics


def test_builtin_validate_metrics():
    fw = get_framework("builtin")
    unsupported = fw.validate_metrics(["accuracy", "totally_made_up"])
    assert unsupported == ["totally_made_up"]


def test_builtin_evaluate_quantitative():
    fw = get_framework("builtin")  # judge_type none -> no LLM calls
    rows = [
        EvalRow(input_text="q1", reference="hello world", response="hello world"),
        EvalRow(input_text="q2", reference="foo bar", response="completely different"),
    ]
    scores = fw.evaluate(rows, ["accuracy", "f1_score"])
    assert scores.framework == "builtin"
    assert len(scores.per_row) == 2
    # Row 0 is an exact match.
    assert scores.per_row[0]["accuracy"] == 1.0
    # Row 1 is not.
    assert scores.per_row[1]["accuracy"] == 0.0
    assert "accuracy" in scores.aggregate
    assert scores.metric_ranges["accuracy"] == [0.0, 1.0]


def test_builtin_judge_metric_neutral_fallback():
    """Without an available judge, qualitative metrics fall back to 3.0/5."""
    fw = BuiltinFramework(judge_type="none")
    rows = [EvalRow(input_text="q", reference="r", response="a")]
    scores = fw.evaluate(rows, ["helpfulness"])
    assert scores.per_row[0]["helpfulness"] == 3.0
    assert scores.metric_ranges["helpfulness"] == [1.0, 5.0]


# ---------------------------------------------------------------------------
# EvaluationConfig manager
# ---------------------------------------------------------------------------

def test_eval_config_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = EvalConfigManager(Path(tmp))
        cfg = EvaluationConfig(
            name="support-eval",
            dataset="support-qa",
            metrics=["accuracy", "f1_score"],
            framework="builtin",
            judge="none",
        )
        assert not mgr.exists("support-eval")
        mgr.save(cfg)
        assert mgr.exists("support-eval")

        loaded = mgr.load("support-eval")
        assert loaded is not None
        assert loaded.dataset == "support-qa"
        assert loaded.metrics == ["accuracy", "f1_score"]

        names = [c.name for c in mgr.list()]
        assert "support-eval" in names

        assert mgr.delete("support-eval") is True
        assert mgr.load("support-eval") is None


def test_eval_config_from_dict_ignores_unknown_keys():
    cfg = EvaluationConfig.from_dict(
        {"name": "x", "dataset": "d", "metrics": ["accuracy"], "bogus": 123}
    )
    assert cfg.name == "x"
    assert cfg.dataset == "d"


# ---------------------------------------------------------------------------
# CSV dataset versioning + register
# ---------------------------------------------------------------------------

def test_csv_dataset_versioning():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = CsvDatasetManager(Path(tmp))
        assert mgr.latest_version("qa") is None

        v1 = mgr.write_new_version(
            "qa",
            [CsvRow(user_input="q1", reference="a1")],
        )
        assert v1 == 1
        v2 = mgr.write_new_version(
            "qa",
            [CsvRow(user_input="q1", reference="a1", response="r1")],
        )
        assert v2 == 2
        assert mgr.list_versions("qa") == [1, 2]
        assert mgr.latest_version("qa") == 2

        rows = mgr.read("qa")  # latest
        assert rows[0].response == "r1"


def test_csv_reference_contexts_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = CsvDatasetManager(Path(tmp))
        mgr.write_new_version(
            "ctx",
            [CsvRow(user_input="q", reference_contexts=["c1", "c2"], reference="a")],
        )
        rows = mgr.read("ctx")
        assert rows[0].reference_contexts == ["c1", "c2"]


def test_csv_register_from_file():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src = tmp_path / "src.csv"
        src.write_text(
            "user_input,reference\n"
            "What is AI?,Artificial Intelligence\n"
            "What is ML?,Machine Learning\n"
        )
        mgr = CsvDatasetManager(tmp_path / "store")
        version = mgr.register_from_file("kb", src)
        assert version == 1
        rows = mgr.read("kb")
        assert len(rows) == 2
        assert rows[0].user_input == "What is AI?"


def test_csv_register_missing_user_input_column():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src = tmp_path / "bad.csv"
        src.write_text("question,answer\nq,a\n")
        mgr = CsvDatasetManager(tmp_path / "store")
        with pytest.raises(ValueError):
            mgr.register_from_file("kb", src)


def test_csv_has_responses():
    rows_full = [CsvRow(user_input="q", response="r")]
    rows_partial = [CsvRow(user_input="q", response="r"), CsvRow(user_input="q2")]
    assert CsvDatasetManager.has_responses(rows_full) is True
    assert CsvDatasetManager.has_responses(rows_partial) is False
    assert CsvDatasetManager.has_responses([]) is False


# ---------------------------------------------------------------------------
# Agent runner
# ---------------------------------------------------------------------------

def test_resolve_agent_mock():
    agent = resolve_agent("mock:helpful")
    assert callable(agent)


def test_resolve_agent_module_function():
    # Resolve a real callable from the stdlib-like path within our package.
    agent = resolve_agent("agentic_cli.evaluation.agent_adapters:MockAgents")
    assert agent is not None


def test_resolve_agent_invalid_spec():
    with pytest.raises(ValueError):
        resolve_agent("no-colon-here")


def test_agent_collector_fills_responses():
    rows = [CsvRow(user_input="hello"), CsvRow(user_input="world")]
    agent = resolve_agent("mock:simple")  # echo agent
    collector = AgentResponseCollector(agent, batch_size=2)
    result = collector.collect(rows)
    assert result[0].response == "hello"
    assert result[1].response == "world"


def test_agent_collector_skips_existing_unless_forced():
    rows = [CsvRow(user_input="hello", response="cached")]
    agent = resolve_agent("mock:simple")
    collector = AgentResponseCollector(agent, batch_size=1)

    # Without force, existing response is preserved.
    collector.collect(rows, force=False)
    assert rows[0].response == "cached"

    # With force, response is recollected (echo -> "hello").
    collector.collect(rows, force=True)
    assert rows[0].response == "hello"


def test_agent_collector_batch_size_clamped():
    agent = resolve_agent("mock:simple")
    assert AgentResponseCollector(agent, batch_size=999).batch_size == 20
    assert AgentResponseCollector(agent, batch_size=0).batch_size == 1


# ---------------------------------------------------------------------------
# Generic class-based agent adapter (BaseAgent-style process() -> dict)
# ---------------------------------------------------------------------------

import asyncio

from agentic_cli.evaluation.agent_runner import (
    _extract_response,
    _wrap_class_agent,
)


class _ProcessAgent:
    """BaseAgent-style: async initialize() + async process(dict) -> dict."""

    def __init__(self, settings=None):
        self.initialized = False

    async def initialize(self):
        self.initialized = True

    async def process(self, input_data):
        return {"response": f"echo:{input_data['message']}", "status": "success"}


class _AltKeyAgent:
    """Async process returning the text under a non-default key."""

    async def process(self, input_data):
        return {"output": f"alt:{input_data['message']}"}


class _AnswerAgent:
    """No process(); exposes a sync string entrypoint named answer()."""

    def answer(self, input_text):
        return f"ans:{input_text}"


def test_wrap_class_agent_process_and_initialize():
    fn = _wrap_class_agent(_ProcessAgent, "mod:_ProcessAgent")
    assert asyncio.run(fn("hi")) == "echo:hi"


def test_wrap_class_agent_extracts_alt_keys():
    fn = _wrap_class_agent(_AltKeyAgent, "mod:_AltKeyAgent")
    assert asyncio.run(fn("x")) == "alt:x"


def test_wrap_class_agent_string_entrypoint():
    fn = _wrap_class_agent(_AnswerAgent, "mod:_AnswerAgent")
    assert asyncio.run(fn("q")) == "ans:q"


def test_extract_response_variants():
    assert _extract_response({"response": "a"}) == "a"
    assert _extract_response({"output": "b"}) == "b"
    assert _extract_response("plain") == "plain"
    assert _extract_response({"no_known_key": 1}) == "{'no_known_key': 1}"


def test_resolve_agent_routes_agent_class():
    # End-to-end: module:ClassName resolves and wraps an agent-like class.
    fn = resolve_agent(f"{__name__}:_ProcessAgent")
    assert callable(fn)
    assert asyncio.run(fn("yo")) == "echo:yo"


def test_resolve_agent_nonagent_class_is_callable_fallback():
    # A class without process/answer/run is treated as a plain callable
    # (backward-compatible), not wrapped as an agent.
    agent = resolve_agent("agentic_cli.evaluation.agent_adapters:MockAgents")
    assert agent is not None
