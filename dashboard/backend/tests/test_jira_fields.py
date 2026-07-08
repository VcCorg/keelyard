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


from src.services.jira_service import _build_issue_fields

FULL = CreateMeta(project_key="CGF", issue_types=["Story"],
    epic_link_field="customfield_10008", story_points_field="customfield_10004",
    acceptance_criteria_field="customfield_10100",
    has_components=True, has_assignee=True, has_priority=True)


def test_build_fields_full():
    f = _build_issue_fields(project_key="CGF", summary="S", description="D",
        issue_type="Story", labels=["a b"], priority="High", epic_key="CGF-1",
        story_points=5, assignee="jdoe", components=["api"],
        acceptance_criteria=["ac1", "ac2"], meta=FULL)
    assert f["project"] == {"key": "CGF"} and f["issuetype"] == {"name": "Story"}
    assert f["labels"] == ["a-b"] and f["priority"] == {"name": "High"}
    assert f["customfield_10008"] == "CGF-1" and f["customfield_10004"] == 5
    assert f["assignee"] == {"name": "jdoe"} and f["components"] == [{"name": "api"}]
    assert f["customfield_10100"] == "ac1\nac2"
    assert "Acceptance criteria" not in f["description"]


def test_build_fields_degrade():
    bare = CreateMeta(project_key="CGF", issue_types=["Story"])
    f = _build_issue_fields(project_key="CGF", summary="S", description="D",
        issue_type="Story", labels=[], priority="High", epic_key="CGF-1",
        story_points=5, assignee="jdoe", components=["api"],
        acceptance_criteria=["ac1"], meta=bare)
    for k in ("customfield_10008", "customfield_10004", "assignee", "components", "priority"):
        assert k not in f
    assert "Acceptance criteria:" in f["description"] and "- ac1" in f["description"]


def test_build_fields_no_meta_permissive():
    f = _build_issue_fields(project_key="CGF", summary="S", description="D",
        issue_type="Story", labels=[], priority="High", epic_key=None,
        story_points=None, assignee=None, components=[], acceptance_criteria=[], meta=None)
    assert f["priority"] == {"name": "High"}
