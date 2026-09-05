"""Tests for run outcomes — a result, and the context that informed it.

Two tests here carry the design.

``test_direction_is_required`` is why :func:`record` has no default: RMSE
improves downward and accuracy upward, so a ranking that assumes one is wrong
half the time — silently, and in the direction that looks like progress.

``test_comparing_different_metrics_raises`` is the other half. Returning False
for "an RMSE did not beat an accuracy" reads as a verdict; there is no ordering
between them and saying so out loud is the only honest option.
"""
from __future__ import annotations

import pytest

from agentic_cli.evaluation import outcomes


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    from agentic_cli import tracker

    db_dir = tmp_path / ".keel-agentic"
    db_dir.mkdir()
    monkeypatch.setattr(tracker, "DB_DIR", db_dir)
    monkeypatch.setattr(tracker, "DB_PATH", db_dir / "tracker.db")
    tracker._ensure_db()
    yield db_dir


def _run_with_context(session, domain, operations, value, metric="public-lb",
                      direction=outcomes.HIGHER):
    from agentic_cli import tracing

    with tracing.session_scope(session, domain=domain):
        for op in operations:
            text = f"{op} body " * 100
            tracing.record_context_read(source="context", operation=op,
                                        entity_id=op, size_bytes=len(text),
                                        payload=text)
    return outcomes.record(session, metric, value, direction=direction,
                           domain=domain)


# ── the contract ────────────────────────────────────────────────────────────

class TestRecording:
    def test_direction_is_required(self):
        """No default, because either default is wrong half the time."""
        with pytest.raises(ValueError, match="direction"):
            outcomes.record("s1", "rmse", 0.12, direction="")
        with pytest.raises(ValueError, match="direction"):
            outcomes.record("s1", "rmse", 0.12, direction="down")

    def test_a_run_and_a_metric_are_both_required(self):
        with pytest.raises(ValueError):
            outcomes.record("", "rmse", 0.1, direction=outcomes.LOWER)
        with pytest.raises(ValueError):
            outcomes.record("s1", "", 0.1, direction=outcomes.LOWER)

    def test_a_non_numeric_value_is_refused(self):
        with pytest.raises(ValueError, match="number"):
            outcomes.record("s1", "rmse", "very good", direction=outcomes.LOWER)

    def test_the_outcome_lands_on_the_session_that_produced_it(self):
        """The join is the whole point: same correlation id as its reads."""
        _run_with_context("sess-1", "titanic", ["resolve/domain"], 0.81)
        [found] = outcomes.for_session("sess-1")
        assert found.metric == "public-lb"
        assert found.value == pytest.approx(0.81)
        assert found.reported_by == ""

    def test_several_results_per_run_are_kept_apart(self):
        """Public and private leaderboards are two numbers, not one."""
        _run_with_context("sess-1", "titanic", ["resolve/domain"], 0.81)
        outcomes.record("sess-1", "private-lb", 0.79, direction=outcomes.HIGHER)
        assert {o.metric for o in outcomes.for_session("sess-1")} == {
            "public-lb", "private-lb"}


class TestComparison:
    def test_comparing_different_metrics_raises(self):
        """"Did not beat" and "not comparable" must not render the same."""
        a = outcomes.Outcome("s1", "rmse", 0.1, outcomes.LOWER)
        b = outcomes.Outcome("s2", "accuracy", 0.9, outcomes.HIGHER)
        with pytest.raises(ValueError, match="no ordering"):
            a.beats(b)

    def test_lower_is_better_inverts_the_comparison(self):
        low = outcomes.Outcome("s1", "rmse", 0.10, outcomes.LOWER)
        high = outcomes.Outcome("s2", "rmse", 0.20, outcomes.LOWER)
        assert low.beats(high)
        assert not high.beats(low)

    def test_higher_is_better_is_the_other_way(self):
        low = outcomes.Outcome("s1", "acc", 0.10, outcomes.HIGHER)
        high = outcomes.Outcome("s2", "acc", 0.20, outcomes.HIGHER)
        assert high.beats(low)


# ── ranking ─────────────────────────────────────────────────────────────────

class TestRanking:
    def test_runs_rank_best_first_by_direction(self):
        _run_with_context("worse", "titanic", ["resolve/domain"], 0.70)
        _run_with_context("better", "titanic", ["resolve/domain"], 0.90)
        assert [r.session_id for r in outcomes.runs(domain="titanic")] == \
            ["better", "worse"]

    def test_lower_is_better_ranks_the_other_way(self):
        _run_with_context("worse", "house", ["resolve/domain"], 0.90,
                          metric="rmse", direction=outcomes.LOWER)
        _run_with_context("better", "house", ["resolve/domain"], 0.10,
                          metric="rmse", direction=outcomes.LOWER)
        assert [r.session_id for r in outcomes.runs(domain="house")] == \
            ["better", "worse"]

    def test_mixed_metrics_are_left_unranked_rather_than_ordered(self):
        """Two metrics have no ordering; inventing one is the failure."""
        _run_with_context("a", "titanic", ["resolve/domain"], 0.90)
        _run_with_context("b", "titanic", ["resolve/domain"], 0.10,
                          metric="rmse", direction=outcomes.LOWER)
        found = outcomes.runs(domain="titanic")
        assert len(found) == 2
        assert len({r.outcome.metric for r in found}) == 2
        assert sorted(outcomes.metrics_seen("titanic")) == ["public-lb", "rmse"]

    def test_naming_a_metric_makes_a_mixed_set_rankable(self):
        _run_with_context("a", "titanic", ["resolve/domain"], 0.90)
        _run_with_context("b", "titanic", ["resolve/domain"], 0.10,
                          metric="rmse", direction=outcomes.LOWER)
        found = outcomes.runs(domain="titanic", metric="public-lb")
        assert [r.session_id for r in found] == ["a"]

    def test_an_unreadable_row_is_skipped_not_zeroed(self):
        """A zero sorts as a real result, which is worse than a missing one."""
        from agentic_cli.tracker import record_activity

        _run_with_context("good", "titanic", ["resolve/domain"], 0.90)
        record_activity(outcomes.SOURCE, "record",
                        entity_type=outcomes.ENTITY_TYPE, entity_id="public-lb",
                        correlation_id="broken", domain="titanic",
                        details={"metric": "public-lb", "value": "not a number"})
        found = outcomes.runs(domain="titanic")
        assert [r.session_id for r in found] == ["good"]

    def test_a_project_with_no_outcomes_returns_nothing(self):
        assert outcomes.runs(domain="never-run") == []


# ── the join that differentiates ────────────────────────────────────────────

class TestContextJoin:
    def test_each_run_carries_what_its_session_read(self):
        _run_with_context("sess-1", "titanic",
                          ["resolve/domain", "read/confluence"], 0.81)
        [run] = outcomes.runs(domain="titanic")
        assert run.context_keys
        assert run.tokens > 0

    def test_the_delta_names_what_differed(self):
        """The backlog's question, reduced to the part Keel can answer."""
        _run_with_context("with-forum", "titanic",
                          ["resolve/domain", "read/confluence"], 0.8134)
        _run_with_context("without", "titanic", ["resolve/domain"], 0.7891)
        found = outcomes.runs(domain="titanic")
        delta = outcomes.context_delta(found[0], found[-1])

        assert delta["value_delta"] == pytest.approx(0.0243)
        assert delta["only_in_better"]          # the forum read
        assert not delta["only_in_worse"]
        assert delta["shared"]
        assert delta["token_delta"] > 0

    def test_an_outcome_with_no_context_still_records(self):
        """Half of the pair is still worth having, and it is visible as half."""
        outcomes.record("orphan", "public-lb", 0.5, direction=outcomes.HIGHER,
                        domain="titanic")
        [run] = outcomes.runs(domain="titanic")
        assert run.sources == {}
        assert run.tokens == 0


class TestScopeDiscipline:
    def test_nothing_here_computes_an_outcome(self):
        """Keel scores context; a leaderboard scores the model.

        The moment this module derives that number it claims authority over
        ground truth it does not have — so the only way a value gets in is by
        being passed to `record`.
        """
        import inspect

        source = inspect.getsource(outcomes)
        for forbidden in ("def evaluate", "def compute", "def measure",
                          "def benchmark"):
            assert forbidden not in source
