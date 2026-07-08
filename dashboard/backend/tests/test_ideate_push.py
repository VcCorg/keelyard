import src.services.ideate_audit as audit


def test_record_success(monkeypatch):
    calls = {}
    monkeypatch.setattr(audit, "_tracker_record_action",
                        lambda feature, action, **kw: calls.update({"f": feature, "a": action, **kw}))
    audit.record_jira_create(project_key="CGF", key="CGF-1", url="u", ok=True,
                             title="S", actor="jdoe@x.com", correlation_id="c1")
    assert calls["f"] == "ideate" and calls["a"] == "jira_create"
    assert calls["status"] == "success" and calls["entity_type"] == "jira_issue"
    assert calls["entity_id"] == "CGF-1" and calls["actor"] == "jdoe@x.com"
    assert calls["source"] == "dashboard" and calls["correlation_id"] == "c1"
    assert calls["details"]["title"] == "S"


def test_record_failure(monkeypatch):
    seen = {}
    monkeypatch.setattr(audit, "_tracker_record_action",
                        lambda feature, action, **kw: seen.update(kw))
    audit.record_jira_create(project_key="CGF", key="", url="", ok=False,
                             title="S", error="boom", actor=None, correlation_id="c1")
    assert seen["status"] == "error" and seen["entity_id"] == "CGF"
    assert seen["details"]["error"] == "boom"


import src.services.ideate_service as isvc
from src.services.ideate_service import Story


def test_push_creates_and_audits(monkeypatch):
    created, audits = [], []
    import src.services.jira_service as js
    monkeypatch.setattr(js, "create_issue", lambda **kw: created.append(kw) or {"key": "CGF-100", "url": "u"})
    monkeypatch.setattr(js, "get_create_meta", lambda pk: None)
    monkeypatch.setattr(audit, "record_jira_create", lambda **kw: audits.append(kw))
    out = isvc.push_stories("CGF", [Story(title="A", acceptance_criteria=["x"], epic_key="CGF-1")], actor="jdoe@x.com")
    assert out["created"] == 1 and out["results"][0]["ok"] and out["results"][0]["key"] == "CGF-100"
    assert created[0]["epic_key"] == "CGF-1" and created[0]["acceptance_criteria"] == ["x"]
    assert len(audits) == 1 and audits[0]["ok"] and audits[0]["actor"] == "jdoe@x.com"


def test_push_audits_failures(monkeypatch):
    audits = []
    import src.services.jira_service as js

    def boom(**kw):
        raise RuntimeError("nope")

    monkeypatch.setattr(js, "create_issue", boom)
    monkeypatch.setattr(js, "get_create_meta", lambda pk: None)
    monkeypatch.setattr(audit, "record_jira_create", lambda **kw: audits.append(kw))
    out = isvc.push_stories("CGF", [Story(title="A")], actor=None)
    assert out["created"] == 0 and out["results"][0]["ok"] is False
    assert "nope" in out["results"][0]["error"] and audits[0]["ok"] is False
