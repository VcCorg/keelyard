"""Offline context metrics — the instrument without a judge.

The built-in framework scores accuracy, f1 and bleu, all reference-based, so a
live session with no ground truth scored nothing at all without Ragas. That made
the Context Playground's whole point — watching scores move when a source is
removed — depend on a cloud credential.

These two metrics are inverses, and the pair is what separates "we are carrying
context nobody reads" from "we just removed the thing holding the answer up".
"""
from __future__ import annotations

import pytest

from agentic_cli.evaluation.frameworks import get_framework
from agentic_cli.evaluation.frameworks.base import EvalRow
from agentic_cli.evaluation.frameworks.heuristic import (
    CONTRIBUTION,
    METRICS,
    UTILIZATION,
    contribution,
    utilization,
)

SETUP = "Setup: run the bootstrap target before your first build."
GLOSSARY = "Glossary: Facility is a physical site where care is delivered."


def _row(response, contexts=(SETUP, GLOSSARY)):
    return EvalRow(input_text="How do I run it?", response=response,
                   retrieved_contexts=list(contexts))


class TestUtilization:
    def test_a_grounded_answer_scores_high(self):
        assert utilization(_row("Run the bootstrap target before your first build.")) > 0.9

    def test_an_ungrounded_answer_scores_zero(self):
        """The signal that matters: the answer stopped coming from the context."""
        assert utilization(_row("Deploy with kubectl to the staging cluster.")) == 0.0

    def test_removing_the_load_bearing_source_drops_utilization(self):
        answer = "Run the bootstrap target before your first build."
        with_setup = utilization(_row(answer))
        without_setup = utilization(_row(answer, contexts=(GLOSSARY,)))
        assert without_setup < with_setup

    def test_an_empty_answer_scores_zero_rather_than_dividing_by_nothing(self):
        assert utilization(_row("")) == 0.0

    def test_stopwords_do_not_inflate_the_score(self):
        """'The and of it' shares every word with any English text."""
        assert utilization(_row("The and of it is to be.")) == 0.0


class TestContribution:
    def test_an_unused_source_lowers_contribution(self):
        """The dead-weight signal — context nobody reads."""
        answer = "Run the bootstrap target before your first build."
        assert contribution(_row(answer)) == pytest.approx(0.5)
        assert contribution(_row(answer, contexts=(SETUP,))) == pytest.approx(1.0)

    def test_no_context_scores_zero(self):
        assert contribution(_row("anything", contexts=())) == 0.0

    def test_no_answer_scores_zero(self):
        assert contribution(_row("")) == 0.0


class TestFramework:
    def _engine(self):
        return get_framework("heuristic")

    def test_registered_and_always_available(self):
        """It exists so the instrument works when nothing else does."""
        engine = self._engine()
        assert engine.name == "heuristic"
        assert engine.available()

    def test_scores_both_metrics(self):
        result = self._engine().evaluate(
            [_row("Run the bootstrap target.")], list(METRICS))
        assert set(result.aggregate) == set(METRICS)
        assert result.framework == "heuristic"
        assert result.metric_ranges[UTILIZATION] == (0.0, 1.0)

    def test_a_judge_metric_is_named_not_silently_dropped(self):
        """A caller asking for faithfulness must learn it was not computed."""
        result = self._engine().evaluate([_row("x")], ["faithfulness", UTILIZATION])
        assert UTILIZATION in result.aggregate
        assert "faithfulness" not in result.aggregate
        assert any("faithfulness" in e for e in result.errors)

    def test_metric_names_do_not_collide_with_ragas(self):
        """A lexical overlap score reported as 'faithfulness' would be read as
        a judgement it is not."""
        from agentic_cli.evaluation.frameworks import ragas_adapter

        ragas_names = set(ragas_adapter._RAGAS_METRICS) | set(ragas_adapter._ASPECT_CRITICS)
        assert not (set(METRICS) & ragas_names)

    def test_needs_no_credential_or_network(self, monkeypatch):
        for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "VERTEX_PROJECT_ID"):
            monkeypatch.delenv(key, raising=False)
        assert self._engine().evaluate([_row("Run the bootstrap target.")],
                                       list(METRICS)).aggregate


class TestFallback:
    def test_ragas_availability_is_probed_not_assumed(self):
        """Constructing RagasFramework succeeds even without ragas — its imports
        are lazy — so a constructor check would never fall back."""
        from agentic_cli.evaluation.frameworks.ragas_adapter import ragas_available

        engine = get_framework("ragas")
        assert engine.available() == ragas_available()

    def test_resolve_falls_back_with_a_note(self, monkeypatch):
        from agentic_cli.evaluation import session_feed
        from agentic_cli.evaluation.frameworks import ragas_adapter

        monkeypatch.setattr(ragas_adapter.RagasFramework, "available", lambda self: False)
        name, note = session_feed.resolve_framework("ragas")
        assert name == "heuristic"
        assert "lexical grounding" in note

    def test_resolve_is_silent_when_the_judge_is_there(self, monkeypatch):
        from agentic_cli.evaluation import session_feed
        from agentic_cli.evaluation.frameworks import ragas_adapter

        monkeypatch.setattr(ragas_adapter.RagasFramework, "available", lambda self: True)
        assert session_feed.resolve_framework("ragas") == ("ragas", "")

    def test_asking_for_heuristics_directly_produces_no_warning(self):
        from agentic_cli.evaluation import session_feed

        assert session_feed.resolve_framework("heuristic") == ("heuristic", "")

    def test_metrics_for_follows_the_framework(self):
        from agentic_cli.evaluation import session_feed

        assert session_feed.metrics_for(framework="heuristic") == list(METRICS)
        assert "faithfulness" in session_feed.metrics_for(framework="ragas")
