"""The KeelTrace eval feed: EvalRow built from a real session.

`EvalRow.retrieved_contexts` existed from the start and nothing populated it,
so every context metric scored against an empty list. These tests pin the join
and, more importantly, the refusals — a session that cannot be scored has to say
which of several different reasons applies, because they have different fixes.
"""
from __future__ import annotations

import pytest

from agentic_cli import payload_store as ps
from agentic_cli.evaluation import session_feed
from agentic_cli.onboarding import redaction


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    import importlib

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv(ps.ENV_BACKEND, raising=False)
    import agentic_cli.tracker
    importlib.reload(agentic_cli.tracker)
    redaction.guard_terms.cache_clear()
    ps.reset_store()
    yield
    ps.reset_store()
    redaction.guard_terms.cache_clear()


def _seed(session="s1", prompt="How do I run it?", response="Run the bootstrap target.",
          contexts=("Setup: run the bootstrap target before building.",)):
    store = ps.get_store()
    if prompt is not None:
        store.put(prompt, session_id=session, source="session", operation="prompt")
    if response is not None:
        store.put(response, session_id=session, source="session", operation="response")
    for i, text in enumerate(contexts):
        store.put(text, session_id=session, source="mcp", operation=f"confluence/get_page/{i}")
    return store


class TestBuild:
    def test_row_carries_the_retrieved_contexts(self, monkeypatch):
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        _seed(contexts=("Context A", "Context B"))

        feed = session_feed.build("s1")
        assert feed.scorable
        assert feed.row.input_text == "How do I run it?"
        assert feed.row.response == "Run the bootstrap target."
        assert set(feed.row.retrieved_contexts) == {"Context A", "Context B"}
        assert feed.row.row_id == "s1"

    def test_the_question_and_answer_are_not_counted_as_context(self, monkeypatch):
        """Scoring an answer against itself would inflate every metric."""
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        _seed(contexts=("Only context",))

        feed = session_feed.build("s1")
        assert feed.contexts == 1
        assert feed.row.retrieved_contexts == ["Only context"]

    def test_a_reference_is_carried_through(self, monkeypatch):
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        _seed()
        assert session_feed.build("s1", reference="ground truth").row.reference == "ground truth"


class TestRefusals:
    """Each reason a session cannot be scored has a different fix."""

    def test_store_disabled(self):
        feed = session_feed.build("s1")
        assert not feed.scorable
        assert any("disabled" in p for p in feed.problems)

    def test_unknown_session(self, monkeypatch):
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        feed = session_feed.build("never-existed")
        assert not feed.scorable
        assert any("No payloads stored" in p for p in feed.problems)

    def test_missing_answer(self, monkeypatch):
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        _seed(response=None)
        feed = session_feed.build("s1")
        assert not feed.scorable
        assert any("No answer recorded" in p for p in feed.problems)

    def test_no_context_is_refused_rather_than_scored_as_zero(self, monkeypatch):
        """An empty context list reads as a failing retriever, not an absent one."""
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        _seed(contexts=())
        feed = session_feed.build("s1")
        assert not feed.scorable
        assert any("empty list" in p for p in feed.problems)

    def test_problems_accumulate_rather_than_short_circuiting(self, monkeypatch):
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        _seed(prompt=None, response=None, contexts=("ctx",))
        assert len(session_feed.build("s1").problems) == 2


class TestLossyReporting:
    def test_masked_context_is_flagged(self, monkeypatch):
        """A score over masked text is not a score over what the agent saw."""
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        _seed(contexts=("Ask Jane Doe at jane@corp.example.net for access.",))

        feed = session_feed.build("s1")
        assert feed.scorable
        assert feed.lossy
        assert "email" in feed.masked_kinds

    def test_clean_context_is_not_flagged(self, monkeypatch):
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        _seed()
        assert not session_feed.build("s1").lossy


class TestMetricSelection:
    def test_default_set_is_reference_free(self):
        """ContextRecall needs ground truth a live session does not have."""
        assert "contextrecall" not in session_feed.metrics_for("")
        assert "faithfulness" in session_feed.metrics_for("")

    def test_a_reference_unlocks_contextrecall(self):
        assert "contextrecall" in session_feed.metrics_for("the right answer")

    def test_every_default_metric_is_known_to_the_adapter(self):
        from agentic_cli.evaluation.frameworks import ragas_adapter

        known = set(ragas_adapter._RAGAS_METRICS) | set(ragas_adapter._ASPECT_CRITICS)
        assert set(session_feed.DEFAULT_METRICS) <= known

    def test_the_default_metrics_do_not_need_a_reference(self):
        """A metric needing ground truth would score every session against ''."""
        from agentic_cli.evaluation.frameworks import ragas_adapter

        for name in session_feed.DEFAULT_METRICS:
            spec = ragas_adapter._RAGAS_METRICS.get(name)
            assert spec is not None and not spec["needs_reference"], name


class TestAskIntegration:
    def test_ask_binds_a_trace_and_records_both_sides(self, monkeypatch):
        """An ask's retrieval used to be orphaned from the answer it produced."""
        import importlib

        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        import agentic_cli.tracing as tracing
        importlib.reload(tracing)

        from agentic_cli.execution import registry
        from agentic_cli.execution.base import AskResult, ExecutionSpec

        class _Engine:
            name = "fake"

            def ask(self, spec):
                # Retrieval happens inside the engine, under the bound trace id.
                tracing.record_context_read(
                    source="mcp", operation="confluence/get_page",
                    payload="Setup: run the bootstrap target.")
                return AskResult(engine=self.name, answer="Run bootstrap.")

        monkeypatch.setattr(registry, "get_engine", lambda name=None: _Engine())

        result = registry.ask(ExecutionSpec(prompt="How do I run it?"))
        assert result.trace_id

        feed = session_feed.build(result.trace_id)
        assert feed.scorable, feed.problems
        assert feed.row.input_text == "How do I run it?"
        assert feed.row.response == "Run bootstrap."
        assert feed.row.retrieved_contexts == ["Setup: run the bootstrap target."]

    def test_ask_still_works_with_the_store_off(self, monkeypatch):
        import importlib

        import agentic_cli.tracing as tracing
        importlib.reload(tracing)

        from agentic_cli.execution import registry
        from agentic_cli.execution.base import AskResult, ExecutionSpec

        class _Engine:
            name = "fake"

            def ask(self, spec):
                return AskResult(engine=self.name, answer="an answer")

        monkeypatch.setattr(registry, "get_engine", lambda name=None: _Engine())
        result = registry.ask(ExecutionSpec(prompt="q"))
        assert result.answer == "an answer"
        assert result.trace_id
        assert not session_feed.build(result.trace_id).scorable


class TestCommandWiring:
    """The last mile: the command hands the built row to the framework."""

    def _run(self, monkeypatch, judge_available=True, **kwargs):
        """Drive the command with a stub framework.

        ``judge_available`` models the two states the command branches on: a
        judge that can run, and one that cannot and must fall back. The stub
        plays both the judge being probed and the framework doing the scoring,
        so it has to answer the probe honestly or the fallback never triggers.
        """
        from agentic_cli.commands import eval as eval_cmd
        from agentic_cli.evaluation.frameworks.base import EvalScores

        seen = {}

        class _Framework:
            name = "stub"

            def available(self):
                return judge_available

            def evaluate(self, rows, metrics, **_):
                seen["rows"] = rows
                seen["metrics"] = metrics
                return EvalScores(framework="stub",
                                  aggregate={m: 0.5 for m in metrics})

        monkeypatch.setattr(
            "agentic_cli.evaluation.frameworks.get_framework",
            lambda name, **kw: _Framework())
        try:
            eval_cmd.eval_session("s1", framework="stub", **kwargs)
        except Exception:  # typer.Exit is click's Exit, not SystemExit
            pass
        return seen

    def test_the_row_reaches_the_framework_with_its_contexts(self, monkeypatch):
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        _seed(contexts=("Context A", "Context B"))

        seen = self._run(monkeypatch, reference=None, metrics=None, as_json=False)
        [row] = seen["rows"]
        assert row.input_text == "How do I run it?"
        assert len(row.retrieved_contexts) == 2
        assert "contextrecall" not in seen["metrics"]

    def test_explicit_metrics_override_the_default_set(self, monkeypatch):
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        _seed()
        seen = self._run(monkeypatch, reference=None, metrics="faithfulness", as_json=False)
        assert seen["metrics"] == ["faithfulness"]

    def test_a_reference_widens_the_metric_set_when_a_judge_is_there(self, monkeypatch):
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        _seed()
        seen = self._run(monkeypatch, reference="ground truth", metrics=None, as_json=False)
        assert "contextrecall" in seen["metrics"]

    def test_a_reference_widens_nothing_without_a_judge(self, monkeypatch):
        """ContextRecall needs a judge as well as ground truth; the offline
        metrics cannot compute it, so a reference buys nothing."""
        from agentic_cli.evaluation.frameworks.heuristic import METRICS

        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        _seed()
        seen = self._run(monkeypatch, judge_available=False,
                         reference="ground truth", metrics=None, as_json=False)
        assert seen["metrics"] == list(METRICS)

    def test_an_unscorable_session_never_reaches_the_framework(self, monkeypatch):
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        _seed(response=None)
        assert self._run(monkeypatch, reference=None, metrics=None, as_json=False) == {}
