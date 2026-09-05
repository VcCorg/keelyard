"""Drift as an event source, and the context sensor that feeds the ledger.

Two Tier-1 pieces. ``onboarding.drift`` moves detection into the CLI so a
watcher poll and a dashboard page cannot disagree about what drift means, and
``context.resolve`` records what Keel assembles into a session's context — the
onboarding material this platform generates was previously read with no trace
that it had been.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from agentic_cli.onboarding import drift


class TestDriftRegistry:
    def test_builtin_detectors_are_registered(self):
        assert {"docs", "instructions", "repo-sources", "template",
                "placeholder"} <= set(drift.detector_keys())

    def test_a_failing_detector_becomes_a_signal_not_an_exception(self):
        """A page and a background poll both read this; neither may crash."""
        def boom(slug):
            raise RuntimeError("source misconfigured")

        drift.register_detector("explodes", boom)
        try:
            signals = drift.detect("any-domain", keys=["explodes"])
        finally:
            drift._DETECTORS.pop("explodes", None)

        assert len(signals) == 1
        assert signals[0].severity == drift.WARN
        assert "unknown" in signals[0].fix

    def test_detector_returning_none_is_omitted(self):
        drift.register_detector("quiet", lambda slug: None)
        try:
            assert drift.detect("d", keys=["quiet"]) == []
        finally:
            drift._DETECTORS.pop("quiet", None)

    def test_keys_filter_selects_detectors(self):
        drift.register_detector("a", lambda s: drift.DriftSignal("a", "A"))
        drift.register_detector("b", lambda s: drift.DriftSignal("b", "B"))
        try:
            assert [s.key for s in drift.detect("d", keys=["b"])] == ["b"]
        finally:
            for key in ("a", "b"):
                drift._DETECTORS.pop(key, None)

    def test_severity_ordering(self):
        assert drift.DriftSignal("k", "L", severity=drift.FAIL).at_least(drift.WARN)
        assert not drift.DriftSignal("k", "L", severity=drift.WARN).at_least(drift.FAIL)
        assert drift.worst([
            drift.DriftSignal("a", "A", severity=drift.OK),
            drift.DriftSignal("b", "B", severity=drift.FAIL),
        ]) == drift.FAIL

    def test_worst_of_nothing_is_ok(self):
        assert drift.worst([]) == drift.OK


class TestDriftTrigger:
    def _fetch(self, filter_):
        from agentic_cli.watchers.registry import get_trigger

        trigger = get_trigger("keel.drift.detected")
        since = datetime(2020, 1, 1, tzinfo=timezone.utc)
        return asyncio.run(trigger.fetch(filter_, since))

    def test_registered(self):
        from agentic_cli.watchers.registry import get_trigger

        assert get_trigger("keel.drift.detected").info.name == "keel.drift.detected"

    def test_no_domain_yields_nothing(self):
        assert self._fetch({}) == []

    def test_emits_one_event_per_actionable_signal(self):
        drift.register_detector("t1", lambda s: drift.DriftSignal(
            "t1", "One", count=2, total=5, severity=drift.FAIL))
        drift.register_detector("t2", lambda s: drift.DriftSignal(
            "t2", "Two", severity=drift.OK))
        try:
            events = self._fetch({"domain": "d", "signals": "t1,t2"})
        finally:
            for key in ("t1", "t2"):
                drift._DETECTORS.pop(key, None)

        assert len(events) == 1
        assert events[0].data["signal"] == "t1"
        assert events[0].data["count"] == 2

    def test_min_severity_widens_to_warnings(self):
        drift.register_detector("w", lambda s: drift.DriftSignal(
            "w", "Warn", severity=drift.WARN))
        try:
            assert self._fetch({"domain": "d", "signals": "w"}) == []
            widened = self._fetch({"domain": "d", "signals": "w", "min_severity": "warn"})
        finally:
            drift._DETECTORS.pop("w", None)
        assert len(widened) == 1

    def test_unchanged_drift_keeps_its_event_id(self):
        """Unresolved drift must not re-fire on every poll."""
        drift.register_detector("s", lambda s: drift.DriftSignal(
            "s", "S", count=1, severity=drift.FAIL))
        try:
            first = self._fetch({"domain": "d", "signals": "s"})
            second = self._fetch({"domain": "d", "signals": "s"})
        finally:
            drift._DETECTORS.pop("s", None)
        assert first[0].event_id == second[0].event_id

    def test_worsening_drift_gets_a_new_event_id(self):
        """A handler that reported one conflict should wake when it becomes three."""
        counts = iter([1, 3])
        drift.register_detector("s", lambda s: drift.DriftSignal(
            "s", "S", count=next(counts), severity=drift.FAIL))
        try:
            first = self._fetch({"domain": "d", "signals": "s"})
            second = self._fetch({"domain": "d", "signals": "s"})
        finally:
            drift._DETECTORS.pop("s", None)
        assert first[0].event_id != second[0].event_id

    def test_a_detector_blowing_up_does_not_break_the_poll(self):
        drift.register_detector("boom", lambda s: (_ for _ in ()).throw(RuntimeError("x")))
        try:
            events = self._fetch({"domain": "d", "signals": "boom", "min_severity": "warn"})
        finally:
            drift._DETECTORS.pop("boom", None)
        assert len(events) == 1  # reported as a signal, not raised


class TestContextSensor:
    """`context.resolve` is where Keel assembles a session's context."""

    def test_domain_ref_resolves_and_strips_frontmatter(self, tmp_path, monkeypatch):
        from agentic_cli.context import resolve

        meta = tmp_path / "acme-context-meta"
        (meta / ".domain").mkdir(parents=True)
        (meta / ".domain" / "setup.md").write_text(
            "---\nprovenance: repo:x\nreviewed: yes\n---\n# Setup\n\n- Run bootstrap\n",
            encoding="utf-8")
        monkeypatch.setattr(
            "agentic_cli.meta_repo.detector.detect_domain_meta_repo",
            lambda slug, search_paths=None: meta)

        [item] = resolve.resolve_refs(["domain://acme/setup.md"])
        assert item.resolved
        assert "provenance" not in item.body
        assert "Run bootstrap" in item.body

    def test_domain_ref_cannot_escape_the_domain_directory(self, tmp_path, monkeypatch):
        """A context ref is caller-supplied; '../' is a context ref too."""
        from agentic_cli.context import resolve

        meta = tmp_path / "acme-context-meta"
        (meta / ".domain").mkdir(parents=True)
        (tmp_path / "secret.txt").write_text("do not read me", encoding="utf-8")
        monkeypatch.setattr(
            "agentic_cli.meta_repo.detector.detect_domain_meta_repo",
            lambda slug, search_paths=None: meta)

        [item] = resolve.resolve_refs(["domain://acme/../../secret.txt"])
        assert not item.resolved
        assert "do not read me" not in item.body

    def test_resolution_is_recorded_in_the_ledger(self, tmp_path, monkeypatch):
        from agentic_cli import tracing
        from agentic_cli.context import resolve

        recorded = []
        monkeypatch.setattr(
            tracing, "record_context_read",
            lambda **kw: recorded.append(kw))
        monkeypatch.setattr(resolve.tracing, "record_context_read",
                            lambda **kw: recorded.append(kw))

        resolve.resolve_refs(["okf://d/c", "domain://d/setup.md", "plain-ref"])

        operations = [r["operation"] for r in recorded]
        assert operations == ["resolve/okf", "resolve/domain", "resolve/external"]
        assert all(r["source"] == resolve.TRACE_SOURCE for r in recorded)

    def test_an_unresolvable_ref_is_recorded_not_skipped(self, monkeypatch):
        """A missing source should show up as a gap, not as silence.

        Which *kind* of gap is the distinction the seam exists to keep: an OKF
        bundle that was never exported is a source we could not ask, and it
        records as an error, where a ref with nothing behind it records empty.
        Collapsing the two is how an unreachable source comes to look like a
        source with nothing to say.
        """
        from agentic_cli.context import resolve

        recorded = []
        monkeypatch.setattr(resolve.tracing, "record_context_read",
                            lambda **kw: recorded.append(kw))
        resolve.resolve_refs(["okf://nope/nothing"])
        assert recorded[0]["status"] == "error"
        assert recorded[0]["extra"]["outcome"] == "unavailable"

        recorded.clear()
        resolve.resolve_refs(["plain-ref"])
        assert recorded[0]["status"] == "empty"

    def test_domain_context_refs_lists_finalized_files(self, tmp_path, monkeypatch):
        from agentic_cli.context import resolve

        meta = tmp_path / "acme-context-meta"
        (meta / ".domain").mkdir(parents=True)
        for name in ("setup.md", "glossary.md"):
            (meta / ".domain" / name).write_text("body\n", encoding="utf-8")
        monkeypatch.setattr(
            "agentic_cli.meta_repo.detector.detect_domain_meta_repo",
            lambda slug, search_paths=None: meta)

        assert resolve.domain_context_refs("acme") == [
            "domain://acme/glossary.md", "domain://acme/setup.md"]

    def test_placeholder_content_is_never_served_as_context(self, tmp_path, monkeypatch):
        """`domain init` writes filler when the KG is empty; an agent handed
        that reads it as a statement about the domain."""
        from agentic_cli.context import resolve

        meta = tmp_path / "acme-context-meta"
        (meta / ".domain").mkdir(parents=True)
        (meta / ".domain" / "architecture.md").write_text(
            "# Architecture\n\n_Architecture details will be populated from the "
            "Knowledge Graph._\n", encoding="utf-8")
        (meta / ".domain" / "setup.md").write_text(
            "---\nprovenance: repo:x\nreviewed: yes\n---\n# Setup\n\n- Run bootstrap\n",
            encoding="utf-8")
        monkeypatch.setattr(
            "agentic_cli.meta_repo.detector.detect_domain_meta_repo",
            lambda slug, search_paths=None: meta)

        assert resolve.domain_context_refs("acme") == ["domain://acme/setup.md"]

        [item] = resolve.resolve_refs(["domain://acme/architecture.md"])
        assert not item.resolved
        assert "Knowledge Graph" not in item.body
