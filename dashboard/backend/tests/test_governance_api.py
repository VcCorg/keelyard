"""Tests for the build-governance guidance endpoint."""

from src.api.execution import get_build_governance


async def test_governance_endpoint_domainless_default(monkeypatch, tmp_path):
    import agentic_cli.admin.settings as adm

    monkeypatch.setattr(adm, "SETTINGS_PATH", tmp_path / "admin.json")
    out = await get_build_governance("")
    assert out["level"] == "warn"          # adoption-friendly default
    assert out["source"] == "default"
    assert out["registered_repos"] == []


async def test_governance_endpoint_reads_domain_dial(monkeypatch, tmp_path):
    import yaml

    meta = tmp_path / "domain-alpha-meta" / ".platform" / "config"
    meta.mkdir(parents=True)
    (meta / "governance.yaml").write_text(yaml.dump({"build_governance": "enforce"}))
    (meta / "repos.yaml").write_text(yaml.dump(
        {"repos": [{"slug": "svc-a", "clone_url": "https://x/svc-a.git"}]}))
    monkeypatch.chdir(tmp_path)

    out = await get_build_governance("alpha")
    assert out["level"] == "enforce"
    assert out["meta_repo_found"] is True
    assert out["registered_repos"] == [{"slug": "svc-a", "clone_url": "https://x/svc-a.git"}]
