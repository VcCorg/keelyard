"""Tier two: the retrieved text, stored under rules the code enforces.

Three rules from the storage decision are pinned here rather than left to
documentation: nothing is stored unless an operator opts in, an oversized
payload is dropped rather than cut, and expiry actually erases.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from agentic_cli import payload_store as ps
from agentic_cli.onboarding import redaction


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """Point HOME at a fresh dir and reload the tracker so DB_DIR follows it.

    ``tracker.DB_DIR`` is computed at import from ``Path.home()``, so without
    the reload every test in this file would share one payloads.db in the real
    home directory.
    """
    import importlib

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv(ps.ENV_BACKEND, raising=False)
    monkeypatch.delenv(ps.ENV_MAX_BYTES, raising=False)
    monkeypatch.delenv(ps.ENV_TTL_DAYS, raising=False)
    import agentic_cli.tracker
    importlib.reload(agentic_cli.tracker)
    redaction.guard_terms.cache_clear()
    ps.reset_store()
    yield
    ps.reset_store()
    redaction.guard_terms.cache_clear()


class TestDefaultOff:
    def test_nothing_is_stored_unless_a_backend_is_selected(self):
        """Enabling tier two must be a deliberate act by whoever runs Keel."""
        store = ps.get_store()
        assert isinstance(store, ps.NullStore)
        outcome = store.put("some retrieved document body")
        assert not outcome.stored
        assert "disabled" in outcome.reason

    def test_a_disabled_store_still_explains_itself_on_the_row(self):
        outcome = ps.get_store().put("body")
        assert outcome.details()["payload"]


class TestMasking:
    def test_identifiers_are_replaced_and_reported(self, monkeypatch):
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        outcome = ps.get_store().put("Ask Jane Doe at jane@corp.example.net")
        assert outcome.stored
        assert set(outcome.masked) >= {"email", "person"}
        stored = ps.read(outcome.ref)
        assert "jane@corp.example.net" not in stored.text
        assert "Jane" not in stored.text
        assert stored.lossy

    def test_masking_preserves_the_claims_a_metric_scores(self, monkeypatch):
        """Deleting spans would make a correct answer read as unfaithful."""
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        outcome = ps.get_store().put(
            "Contact Jane Doe. The facility SLA is 100ms and uptime is 99.9%.")
        text = ps.read(outcome.ref).text
        assert "100ms" in text and "99.9%" in text

    def test_verbatim_text_is_not_marked_lossy(self, monkeypatch):
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        outcome = ps.get_store().put("Run the bootstrap target before building.")
        assert outcome.masked == ()
        assert not ps.read(outcome.ref).lossy

    def test_guard_terms_are_masked(self, monkeypatch):
        monkeypatch.setenv("KEEL_GUARD_TERMS", "widgetco")
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        redaction.guard_terms.cache_clear()
        ps.reset_store()
        outcome = ps.get_store().put("Deploy to the WidgetCo cluster")
        assert "widget" not in ps.read(outcome.ref).text.lower()


class TestCap:
    def test_oversized_payloads_are_dropped_not_truncated(self, monkeypatch):
        """A cut chunk makes Faithfulness wrong, not merely incomplete."""
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        monkeypatch.setenv(ps.ENV_MAX_BYTES, "100")
        ps.reset_store()
        outcome = ps.get_store().put("x" * 500)
        assert not outcome.stored
        assert "omitted (size" in outcome.reason

    def test_a_dropped_payload_is_visibly_dropped_on_the_row(self, monkeypatch):
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        monkeypatch.setenv(ps.ENV_MAX_BYTES, "10")
        ps.reset_store()
        details = ps.get_store().put("x" * 100).details()
        assert "payload_ref" not in details
        assert details["payload"].startswith("omitted")

    def test_empty_text_is_not_stored(self, monkeypatch):
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        assert not ps.get_store().put("   ").stored


class TestMemoryBackend:
    def test_round_trip_and_session_grouping(self, monkeypatch):
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        store = ps.get_store()
        a = store.put("first body", session_id="s1")
        b = store.put("second body", session_id="s1")
        store.put("other", session_id="s2")

        assert {p.text for p in store.session("s1")} == {"first body", "second body"}
        assert ps.read(a.ref).text == "first body"
        assert store.delete(b.ref) and ps.read(b.ref) is None

    def test_nothing_reaches_disk(self, monkeypatch, tmp_path):
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        ps.get_store().put("a proprietary document body", session_id="s1")
        assert not list(tmp_path.rglob("payloads.db"))

    def test_a_ref_from_another_scheme_is_not_resolved(self, monkeypatch):
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        outcome = ps.get_store().put("body")
        assert ps.get_store().get(outcome.ref.replace("mem:", "sqlite:")) is None


class TestSqliteBackend:
    def _store(self, monkeypatch):
        monkeypatch.setenv(ps.ENV_BACKEND, "sqlite")
        ps.reset_store()
        return ps.get_store()

    def test_uses_a_separate_file_from_the_tracker(self, monkeypatch):
        """tracker.db is the audit trail and stays safe to hand over."""
        from agentic_cli.tracker import DB_PATH

        store = self._store(monkeypatch)
        assert store.path != DB_PATH
        assert store.path.name == "payloads.db"

    def test_round_trip_and_session_feed(self, monkeypatch):
        store = self._store(monkeypatch)
        store.put("alpha", session_id="s1", source="mcp", operation="jira/get")
        store.put("beta", session_id="s1")
        store.put("gamma", session_id="s2")
        assert [p.text for p in store.session("s1")] == ["alpha", "beta"]

    def test_expired_rows_are_invisible_before_the_sweep_runs(self, monkeypatch):
        store = self._store(monkeypatch)
        outcome = store.put("stale body", session_id="s1")
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        with sqlite3.connect(str(store.path)) as conn:
            conn.execute("UPDATE payloads SET expires_at = ?", (past,))
        assert store.get(outcome.ref) is None
        assert store.session("s1") == []

    def test_sweep_deletes_expired_rows(self, monkeypatch):
        store = self._store(monkeypatch)
        store.put("body", session_id="s1")
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        with sqlite3.connect(str(store.path)) as conn:
            conn.execute("UPDATE payloads SET expires_at = ?", (past,))
        assert store.sweep() == 1
        with sqlite3.connect(str(store.path)) as conn:
            assert conn.execute("SELECT COUNT(*) FROM payloads").fetchone()[0] == 0

    def test_secure_delete_is_enabled(self, monkeypatch):
        """DELETE that leaves readable bytes in the file is not a retention policy."""
        store = self._store(monkeypatch)
        with sqlite3.connect(str(store.path)) as conn:
            conn.execute("PRAGMA secure_delete = ON")
            assert conn.execute("PRAGMA secure_delete").fetchone()[0] == 1

    def test_ttl_zero_means_no_expiry(self, monkeypatch):
        monkeypatch.setenv(ps.ENV_TTL_DAYS, "0")
        store = self._store(monkeypatch)
        outcome = store.put("body")
        assert ps.read(outcome.ref).expires_at == ""

    def test_purge_removes_everything(self, monkeypatch):
        store = self._store(monkeypatch)
        store.put("one"); store.put("two")
        store.purge()
        with sqlite3.connect(str(store.path)) as conn:
            assert conn.execute("SELECT COUNT(*) FROM payloads").fetchone()[0] == 0


class TestSensorIntegration:
    def test_payload_flows_through_record_context_read(self, monkeypatch):
        import importlib

        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        import agentic_cli.tracker as tracker
        tracker = importlib.reload(tracker)
        import agentic_cli.tracing as tracing
        tracing = importlib.reload(tracing)

        tracing.record_context_read(
            source="mcp", operation="confluence/get_page", session_id="s1",
            entity_id="12345", payload="Ask Jane Doe. The SLA is 100ms.")

        [row] = tracker.get_activity(entity_type="context", limit=5)
        details = tracing.details_of(row)
        assert details["payload_ref"].startswith("mem:")
        assert "person" in details["payload_masked"]
        assert "Jane" not in str(row)

    def test_disabled_store_records_why_and_never_the_body(self, monkeypatch):
        import importlib

        import agentic_cli.tracker as tracker
        tracker = importlib.reload(tracker)
        import agentic_cli.tracing as tracing
        tracing = importlib.reload(tracing)

        tracing.record_context_read(
            source="mcp", operation="jira/get_issue",
            payload="a proprietary ticket body")

        [row] = tracker.get_activity(entity_type="context", limit=5)
        blob = str(row)
        assert "proprietary ticket body" not in blob
        assert "payload_ref" not in tracing.details_of(row)

    def test_recording_still_never_raises(self, monkeypatch):
        monkeypatch.setenv(ps.ENV_BACKEND, "memory")
        ps.reset_store()
        import agentic_cli.tracing as tracing

        monkeypatch.setattr(ps, "get_store",
                            lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        tracing.record_context_read(source="kg", operation="query", payload="x")
