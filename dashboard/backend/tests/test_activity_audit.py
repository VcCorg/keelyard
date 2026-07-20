"""Tests for the audit-trail filters on the activity service (keel history gap)."""

import importlib

import pytest


@pytest.fixture()
def tracker(tmp_path, monkeypatch):
    """Point the tracker at a temp DB so tests don't touch the real one."""
    import agentic_cli.tracker as tr

    db_dir = tmp_path / ".keel-tracker"
    db_dir.mkdir()
    monkeypatch.setattr(tr, "DB_DIR", db_dir)
    monkeypatch.setattr(tr, "DB_PATH", db_dir / "tracker.db")
    return tr


def test_source_actor_entity_filters(tracker):
    from src.services import activity_service as svc

    tracker.record_action("code", "onboard", entity_type="repo", entity_id="/x/repo-a",
                          source="dashboard", actor="alice@example.com")
    tracker.record_action("skill", "trial", entity_type="skill", entity_id="my-skill",
                          source="cli", actor="bob@example.com")
    tracker.record_action("kg", "ingest", entity_type="domain", entity_id="payments",
                          source="dashboard", actor="alice@example.com")

    # Every audit dimension surfaces through the service model.
    all_rows = svc.get_activity(limit=50)
    assert len(all_rows) == 3
    row = next(r for r in all_rows if r.command == "code")
    assert row.source == "dashboard" and row.actor == "alice@example.com"
    assert row.entity_type == "repo" and row.entity_id == "/x/repo-a"

    # Filter by source.
    dash = svc.get_activity(source="dashboard", limit=50)
    assert {r.command for r in dash} == {"code", "kg"}

    # Filter by actor.
    bob = svc.get_activity(actor="bob@example.com", limit=50)
    assert len(bob) == 1 and bob[0].command == "skill"

    # Filter by entity_type.
    domains = svc.get_activity(entity_type="domain", limit=50)
    assert len(domains) == 1 and domains[0].entity_id == "payments"


def test_filters_compose(tracker):
    from src.services import activity_service as svc

    tracker.record_action("code", "onboard", source="dashboard", actor="alice@example.com")
    tracker.record_action("code", "onboard", source="cli", actor="alice@example.com")

    rows = svc.get_activity(command="code", source="cli", actor="alice@example.com", limit=50)
    assert len(rows) == 1 and rows[0].source == "cli"


def test_tracker_get_activity_accepts_audit_filters(tracker):
    # Direct tracker-level contract the service relies on.
    tracker.record_action("mcp", "register", source="dashboard", actor="carol@example.com",
                          entity_type="mcp", entity_id="remote-1")
    rows = tracker.get_activity(source="dashboard", actor="carol@example.com",
                                entity_type="mcp", limit=10)
    assert len(rows) == 1 and rows[0]["entity_id"] == "remote-1"
