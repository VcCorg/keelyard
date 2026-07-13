"""Tests for the shared persona skill-policy evaluator."""

from pathlib import Path

from agentic_cli.meta_repo.skill_policy import (
    DENIED,
    OUT_OF_POLICY,
    PERMITTED,
    Enforcer,
    default_policy,
    is_permitted,
    load_persona_policy,
    match_token,
    resolve_rule,
    status_for,
)


def test_match_token_tiers_and_globs():
    assert match_token("*", "anything", "agent-skill", "dev")
    assert match_token("domain-validated", "x", "domain-validated", "qa")
    assert match_token("persona:self", "qa", "persona", "qa")
    assert not match_token("persona:self", "dev", "persona", "qa")
    assert match_token("persona:dev", "dev", "persona", "qa")
    assert match_token("persona", "dev", "persona", "qa")
    assert match_token("linked", "x", "linked:app", "dev")
    assert match_token("linked:*", "x", "linked:app", "dev")
    assert match_token("testing-*", "testing-harness", "agent-skill", "qa")
    assert not match_token("testing-*", "water-check", "agent-skill", "qa")


def test_status_allow_list_persona():
    rule = resolve_rule(default_policy(), "qa")  # allow-list only
    assert status_for("facility-sync", "domain-validated", "qa", rule) == PERMITTED
    assert status_for("testing-harness", "agent-skill", "qa", rule) == PERMITTED
    assert status_for("water-check", "agent-skill", "qa", rule) == OUT_OF_POLICY


def test_status_specific_deny_wins():
    rule = {"allow": ["*"], "deny": ["prod-deploy"]}
    assert status_for("prod-deploy", "agent-skill", "dev", rule) == DENIED
    assert status_for("other", "agent-skill", "dev", rule) == PERMITTED


def test_is_permitted_matches_status():
    rule = resolve_rule(default_policy(), "dev")
    assert is_permitted("anything", "agent-skill", "dev", rule) is True


def test_enforcer_records_blocks():
    e = Enforcer("qa", default_policy())
    assert e.allow("facility-sync", "domain-validated") is True
    assert e.allow("water-check", "agent-skill") is False
    assert [b["name"] for b in e.blocked] == ["water-check"]
    assert e.blocked[0]["status"] == OUT_OF_POLICY


def test_load_policy_from_meta_repo(tmp_path):
    cfg = tmp_path / ".platform" / "config"
    cfg.mkdir(parents=True)
    (cfg / "skills.yaml").write_text(
        "personas:\n"
        "  dev:\n    allow: ['*']\n    deny: [prod-deploy]\n",
        encoding="utf-8",
    )
    policy = load_persona_policy(tmp_path)
    assert policy["dev"]["deny"] == ["prod-deploy"]


def test_load_policy_falls_back_to_default(tmp_path):
    # No skills.yaml present -> built-in default policy.
    policy = load_persona_policy(tmp_path)
    assert "qa" in policy and policy["qa"]["deny"] == ["*"]
