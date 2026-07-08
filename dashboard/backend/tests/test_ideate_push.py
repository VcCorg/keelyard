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
