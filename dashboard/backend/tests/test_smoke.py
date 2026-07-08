def test_imports():
    from src.services import ideate_service, jira_service  # noqa: F401


def test_story_extended_fields():
    from src.services.ideate_service import Story
    s = Story(title="X", issue_type="Task", epic_key="ABC-1",
              story_points=3, assignee="jdoe", components=["api"])
    assert (s.issue_type, s.epic_key, s.story_points, s.assignee, s.components) == \
           ("Task", "ABC-1", 3, "jdoe", ["api"])


def test_story_defaults():
    from src.services.ideate_service import Story
    s = Story(title="X")
    assert s.issue_type == "Story" and s.epic_key is None and s.story_points is None
    assert s.assignee is None and s.components == []
