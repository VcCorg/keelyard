"""Tests for per-domain build governance (policy resolver + seam gates)."""

import pytest
import yaml

from agentic_cli.meta_repo import build_governance as bg
from agentic_cli.meta_repo.config import GovernanceConfig


def _make_domain(tmp_path, slug, level=None, repos=None):
    """Create a minimal domain meta-repo with governance.yaml (+ repos.yaml)."""
    meta = tmp_path / f"domain-{slug}-meta"
    cfg = meta / ".platform" / "config"
    cfg.mkdir(parents=True)
    gov = {"branch_pattern": "x"}
    if level is not None:
        gov["build_governance"] = level
    (cfg / "governance.yaml").write_text(yaml.dump(gov), encoding="utf-8")
    if repos is not None:
        (cfg / "repos.yaml").write_text(
            yaml.dump({"repos": [{"slug": r, "clone_url": f"https://x/{r}.git"}
                                 for r in repos]}), encoding="utf-8")
    return meta


@pytest.fixture()
def admin_default(monkeypatch, tmp_path):
    """Pin the admin default (and isolate the settings store)."""
    import agentic_cli.admin.settings as adm

    path = tmp_path / "admin-settings.json"
    monkeypatch.setattr(adm, "SETTINGS_PATH", path)

    def set_default(level):
        adm.set_build_governance_default(level, path)
    return set_default


# ── GovernanceConfig field ───────────────────────────────────────────────────

def test_governance_config_field_round_trips():
    assert GovernanceConfig().build_governance == "warn"
    assert GovernanceConfig.from_dict({"build_governance": "enforce"}).build_governance == "enforce"
    assert GovernanceConfig.from_dict({"build_governance": "bogus"}).build_governance == "warn"
    assert "build_governance" in GovernanceConfig().to_dict()


# ── resolver ─────────────────────────────────────────────────────────────────

def test_domainless_uses_admin_default(admin_default):
    admin_default("enforce")
    p = bg.resolve("")
    assert p.level == "enforce" and p.source == "default"


def test_domain_reads_its_own_dial(tmp_path, admin_default):
    admin_default("enforce")  # must NOT leak into domain-scoped work
    _make_domain(tmp_path, "alpha", level="off")
    p = bg.resolve("alpha", cwd=tmp_path)
    assert p.level == "off" and p.source == "domain:alpha"


def test_missing_meta_repo_falls_back_to_default(tmp_path, admin_default):
    admin_default("warn")
    p = bg.resolve("ghost", cwd=tmp_path)
    assert p.level == "warn" and p.source == "default:meta-repo-missing"


# ── session gate ─────────────────────────────────────────────────────────────

def test_session_without_domain_blocked_when_default_enforce(admin_default):
    admin_default("enforce")
    policy = bg.check_session("")
    assert policy.blocked
    with pytest.raises(bg.GovernanceViolation, match="no domain"):
        bg.enforce_or_raise(policy, "create_session")


def test_session_without_domain_tagged_when_warn(admin_default):
    admin_default("warn")
    policy = bg.check_session("")
    assert not policy.blocked and policy.tagged
    assert policy.audit_details()["governance_level"] == "warn"
    bg.enforce_or_raise(policy, "create_session")  # no raise


def test_session_in_governed_domain_is_clean(tmp_path, admin_default):
    admin_default("enforce")
    _make_domain(tmp_path, "alpha", level="enforce")
    policy = bg.check_session("alpha", cwd=tmp_path)
    assert not policy.violations and not policy.blocked and not policy.tagged


def test_sandbox_domain_off_never_blocks_or_tags(tmp_path, admin_default):
    admin_default("enforce")
    _make_domain(tmp_path, "sandbox", level="off")
    policy = bg.check_session("sandbox", cwd=tmp_path)
    assert not policy.blocked and not policy.tagged  # off = silent sandbox


# ── onboard gate ─────────────────────────────────────────────────────────────

def test_onboard_repo_must_be_registered_when_enforced(tmp_path):
    _make_domain(tmp_path, "alpha", level="enforce", repos=["svc-a", "svc-b"])
    ok = bg.check_onboard("alpha", repo_slug="svc-a", cwd=tmp_path)
    assert not ok.violations

    bad = bg.check_onboard("alpha", project_name="rogue-repo", cwd=tmp_path)
    assert bad.blocked
    with pytest.raises(bg.GovernanceViolation, match="rogue-repo"):
        bg.enforce_or_raise(bad, "code onboard")


def test_onboard_domain_with_no_registered_repos_is_permissive(tmp_path):
    # A domain that registers no repos can't meaningfully restrict them.
    _make_domain(tmp_path, "alpha", level="enforce", repos=[])
    p = bg.check_onboard("alpha", project_name="anything", cwd=tmp_path)
    assert not p.violations


def test_registry_create_session_enforces(admin_default, monkeypatch):
    """The execution seam actually refuses a domainless spec under enforce."""
    admin_default("enforce")
    from agentic_cli.execution import registry
    from agentic_cli.execution.base import ExecutionSpec

    with pytest.raises(bg.GovernanceViolation):
        registry.create_session(ExecutionSpec(prompt="do things"), engine="local")
