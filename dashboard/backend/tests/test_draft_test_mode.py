"""Story drafting must work with NO model configured (built-in test mode)."""

import pytest

from src.services.ideate_service import draft_stories


@pytest.fixture()
def no_model_configured(monkeypatch):
    for var in ("KEEL_LLM_PROVIDER", "KEEL_LOCAL_LLM_MODEL", "KEEL_LOCAL_LLM_URL",
                "KEEL_DISABLE_TEST_MODE"):
        monkeypatch.delenv(var, raising=False)
    import agentic_cli.kg.config as kg_config

    monkeypatch.setattr(
        kg_config.KGConfig, "load",
        classmethod(lambda cls: (_ for _ in ()).throw(RuntimeError("no config"))))


def test_draft_stories_without_any_model(no_model_configured):
    result = draft_stories(
        "Users need offline exports and audit logging for compliance reviews.",
        count=3)
    # The test-mode provider answered through the LLM path (not the heuristic),
    # producing schema-compliant, clearly-labeled stories.
    assert result.source == "llm"
    assert 1 <= len(result.stories) <= 3
    for s in result.stories:
        assert s.title and s.description and s.acceptance_criteria
        assert "test-mode" in s.title or any("test-mode" in c for c in s.acceptance_criteria)
