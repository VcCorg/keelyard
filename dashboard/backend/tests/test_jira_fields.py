from src.services.jira_service import _parse_create_meta, CreateMeta

SAMPLE = {"projects": [{"key": "CGF", "issuetypes": [
    {"name": "Story", "fields": {
        "summary": {"name": "Summary"}, "priority": {"name": "Priority"},
        "components": {"name": "Components"}, "assignee": {"name": "Assignee"},
        "customfield_10008": {"name": "Epic Link"},
        "customfield_10004": {"name": "Story Points"},
        "customfield_10100": {"name": "Acceptance Criteria"}}},
    {"name": "Task", "fields": {"summary": {"name": "Summary"}}}]}]}


def test_parse_meta_discovers_fields():
    m = _parse_create_meta(SAMPLE, "CGF")
    assert isinstance(m, CreateMeta)
    assert m.issue_types == ["Story", "Task"]
    assert m.epic_link_field == "customfield_10008"
    assert m.story_points_field == "customfield_10004"
    assert m.acceptance_criteria_field == "customfield_10100"
    assert m.has_components and m.has_assignee and m.has_priority


def test_parse_meta_missing_project():
    m = _parse_create_meta({"projects": []}, "NOPE")
    assert m.issue_types == [] and m.epic_link_field is None and m.has_components is False
