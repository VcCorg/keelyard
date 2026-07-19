"""Tests for the skill trial + promotion flow."""

import pytest

from src.services import skill_trial_service as svc


@pytest.fixture()
def fake_registry(tmp_path, monkeypatch):
    """A registry with one good skill and one broken skill."""
    reg = tmp_path / "registry"
    good = reg / "skills" / "good-skill"
    good.mkdir(parents=True)
    (good / "SKILL.md").write_text(
        "---\nname: good-skill\ndescription: Validates data pipelines end to end\n---\n"
        + "# Good skill\n" + ("Detailed, actionable guidance. " * 20),
        encoding="utf-8")
    broken = reg / "skills" / "broken-skill"
    broken.mkdir(parents=True)
    (broken / "SKILL.md").write_text("no frontmatter at all", encoding="utf-8")

    import agentic_cli.commands.code as code_mod

    monkeypatch.setattr(code_mod, "_ensure_registry", lambda *_a, **_k: reg)
    # Force AI review to the deterministic test-mode provider.
    monkeypatch.setenv("KEEL_LLM_PROVIDER", "test-mode")
    return reg


def test_trial_scorecard_good_skill(fake_registry):
    card = svc.evaluate_trial("good-skill", domain="", persona="dev", actor="t@x")
    names = {c.name: c.status for c in card.checks}
    assert names["Structure"] == "pass"
    assert names["Persona policy"] == "pass"      # dev default policy: allow *
    assert card.verdict in ("pass", "warn")       # security may be skipped
    assert card.promotable is True


def test_trial_scorecard_broken_skill_fails(fake_registry):
    card = svc.evaluate_trial("broken-skill", domain="", persona="dev")
    names = {c.name: c.status for c in card.checks}
    assert names["Structure"] == "fail"
    assert card.verdict == "fail"
    assert card.promotable is False


def test_trial_unknown_skill_raises(fake_registry):
    with pytest.raises(FileNotFoundError):
        svc.evaluate_trial("nope", domain="", persona="dev")


def test_persona_policy_check_flags_restricted_persona(fake_registry):
    # qa's default policy is allow-list (persona/domain-validated/testing-*):
    # an arbitrary agent-skill is out-of-policy -> warn, not fail.
    card = svc.evaluate_trial("good-skill", domain="", persona="qa")
    names = {c.name: c.status for c in card.checks}
    assert names["Persona policy"] == "warn"
    assert card.promotable is True                # warns don't block promotion


def test_promote_copies_into_domain_context(fake_registry, tmp_path, monkeypatch):
    ctx = tmp_path / "alpha-domain-context"
    ctx.mkdir()
    (ctx / ".domain").write_text("alpha")
    monkeypatch.chdir(tmp_path)

    res = svc.promote_trial("good-skill", "alpha", actor="lead@x")
    dest = ctx / "skills" / "validated" / "good-skill"
    assert dest.is_dir() and (dest / "SKILL.md").is_file()
    assert res.promoted_to == str(dest)


def test_promote_without_context_repo_raises(fake_registry, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError, match="domain-context"):
        svc.promote_trial("good-skill", "ghost")
