"""The Context Playground: replay a session against a different context.

Ablation is what makes the ledger an instrument — a score says a session went
badly, removing a source and re-running says that source was why. These tests
pin the mechanism and the two honest degradations: a replay without a judge
still runs, and a metric the baseline could not score is never reported as a
regression.
"""
from __future__ import annotations

import pytest

from agentic_cli import payload_store as ps
from agentic_cli.evaluation import playground
from agentic_cli.onboarding import redaction


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    import importlib

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv(ps.ENV_BACKEND, "memory")
    import agentic_cli.tracker
    importlib.reload(agentic_cli.tracker)
    redaction.guard_terms.cache_clear()
    ps.reset_store()
    yield
    ps.reset_store()
    redaction.guard_terms.cache_clear()


def _seed(session="s1"):
    store = ps.get_store()
    store.put("How do I run it?", session_id=session, source="session", operation="prompt")
    store.put("Run the bootstrap target.", session_id=session, source="session", operation="response")
    store.put("Setup: run the bootstrap target before building.",
              session_id=session, source="mcp", operation="confluence/get_page")
    store.put("Glossary: Facility is a physical care site.",
              session_id=session, source="kg", operation="query")
    return store


class _Provider:
    """Echoes which context slices it was handed, so ablation is observable."""

    def __init__(self, name="fake/model-1"):
        self._name = name

    def generate(self, prompt):
        seen = [s for s in ("confluence/get_page", "kg/query") if s in prompt]
        return f"[{self._name}] answered using: {', '.join(seen) or 'nothing'}"

    def get_name(self):
        return self._name


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setattr("agentic_cli.llm.factory.get_llm_provider",
                        lambda **kw: _Provider(kw.get("model_name") or "fake/model-1"))


class TestListSources:
    def test_groups_by_source_and_operation(self):
        _seed()
        keys = [s.key for s in playground.list_sources("s1")]
        assert set(keys) == {"mcp/confluence/get_page", "kg/query"}

    def test_the_question_and_answer_are_not_ablatable(self):
        """You cannot switch off the question you are asking."""
        _seed()
        assert all(not s.key.startswith("session/") for s in playground.list_sources("s1"))

    def test_largest_first(self):
        _seed()
        sources = playground.list_sources("s1")
        assert sources[0].bytes >= sources[-1].bytes

    def test_unknown_session_has_no_sources(self):
        assert playground.list_sources("nope") == []


class TestReplay:
    def test_baseline_uses_every_context(self, provider):
        _seed()
        variant = playground.replay("s1")
        assert variant.contexts == 2
        assert "confluence/get_page" in variant.answer and "kg/query" in variant.answer

    def test_excluding_a_source_changes_the_answer(self, provider):
        """The point of the whole surface."""
        _seed()
        variant = playground.replay("s1", exclude=["kg/query"])
        assert variant.contexts == 1
        assert "kg/query" not in variant.answer
        assert "confluence/get_page" in variant.answer

    def test_excluding_everything_still_runs(self, provider):
        _seed()
        variant = playground.replay("s1", exclude=["kg/query", "mcp/confluence/get_page"])
        assert variant.contexts == 0
        assert variant.ran

    def test_a_variant_is_filed_as_its_own_session(self, provider):
        """It must be scorable by the same path as the original, not a parallel one."""
        from agentic_cli.evaluation import session_feed

        _seed()
        variant = playground.replay("s1", exclude=["kg/query"])
        assert variant.trace_id and variant.trace_id != "s1"

        feed = session_feed.build(variant.trace_id)
        assert feed.scorable, feed.problems
        assert feed.row.input_text == "How do I run it?"
        assert feed.contexts == 1

    def test_model_swap_leaves_context_alone(self, provider):
        """The same mechanism, turned the other way."""
        _seed()
        variant = playground.replay("s1", model="other/model-2")
        assert variant.contexts == 2
        assert variant.model == "other/model-2"

    def test_a_session_with_no_question_cannot_be_replayed(self, provider):
        ps.get_store().put("ctx", session_id="s2", source="kg", operation="query")
        variant = playground.replay("s2")
        assert not variant.ran
        assert any("No question" in p for p in variant.problems)

    def test_a_provider_failure_is_a_problem_not_an_exception(self, monkeypatch):
        _seed()

        class _Broken:
            def generate(self, prompt):
                raise RuntimeError("429 rate limited")

            def get_name(self):
                return "broken"

        monkeypatch.setattr("agentic_cli.llm.factory.get_llm_provider",
                            lambda **kw: _Broken())
        variant = playground.replay("s1")
        assert not variant.ran
        assert any("429" in p for p in variant.problems)

    def test_store_variant_false_skips_filing(self, provider):
        _seed()
        variant = playground.replay("s1", store_variant=False)
        assert variant.ran and not variant.trace_id


class TestCompare:
    def test_baseline_plus_one_variant_per_ablation(self, provider):
        _seed()
        comparison = playground.compare(
            "s1", ablations=[["kg/query"], ["mcp/confluence/get_page"]], do_score=False)
        assert comparison.baseline.contexts == 2
        assert [v.contexts for v in comparison.variants] == [1, 1]

    def test_models_become_variants_too(self, provider):
        _seed()
        comparison = playground.compare("s1", models=["m-a", "m-b"], do_score=False)
        assert [v.model for v in comparison.variants] == ["m-a", "m-b"]

    def test_deltas_are_empty_without_a_scored_baseline(self, provider):
        _seed()
        assert playground.compare("s1", ablations=[["kg/query"]], do_score=False).deltas() == []

    def test_deltas_report_movement(self, provider):
        _seed()
        comparison = playground.compare("s1", ablations=[["kg/query"]], do_score=False)
        comparison.baseline.scores = {"faithfulness": 0.9, "responserelevancy": 0.8}
        comparison.variants[0].scores = {"faithfulness": 0.5, "responserelevancy": 0.8}

        [delta] = comparison.deltas()
        assert delta["delta"]["faithfulness"] == pytest.approx(-0.4)
        assert delta["delta"]["responserelevancy"] == pytest.approx(0.0)

    def test_a_metric_the_baseline_could_not_score_is_omitted(self, provider):
        """'We could not measure this' must not render as 'this got worse'."""
        _seed()
        comparison = playground.compare("s1", ablations=[["kg/query"]], do_score=False)
        comparison.baseline.scores = {"faithfulness": 0.9}
        comparison.variants[0].scores = {"faithfulness": 0.9, "contextrecall": 0.2}

        [delta] = comparison.deltas()
        assert "contextrecall" not in delta["delta"]


class TestScoringDegradation:
    def test_an_unscorable_variant_keeps_its_answer(self, provider):
        """No judge degrades the instrument; it does not disable it."""
        _seed()
        variant = playground.replay("s1", exclude=["kg/query"])
        playground.score(variant)
        assert variant.ran
        assert not variant.scored
        assert variant.problems

    def test_scoring_an_unstored_variant_says_so(self, provider):
        _seed()
        variant = playground.replay("s1", store_variant=False)
        playground.score(variant)
        assert any("not stored" in p for p in variant.problems)
