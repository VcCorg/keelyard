"""Tests for meta-repo template manifest + drift classification (phase 1).

Drift detection is the foundation for `template upgrade` / `template promote`,
so the classification table is pinned here: every status must be reachable and
must not be confusable with its neighbours.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_cli.meta_repo import template_drift as drift
from agentic_cli.meta_repo import template_manifest as tm
from agentic_cli.meta_repo.scaffold import scaffold_domain_meta_repo

DOMAIN = "test-facility"
PRODUCT = "TEST"


@pytest.fixture
def meta_repo(tmp_path: Path) -> Path:
    """A freshly scaffolded meta-repo (no git, no personas, no blueprint)."""
    out = tmp_path / "workspace"
    out.mkdir()
    created = scaffold_domain_meta_repo(
        output_dir=out,
        domain=DOMAIN,
        product=PRODUCT,
        description="Test domain",
        owner="owner@example.com",
        git_init=False,
        write_blueprint=False,
    )
    return created["root"]


# ── Manifest ────────────────────────────────────────────────────────────────

def test_scaffold_writes_template_manifest(meta_repo: Path):
    manifest_path = meta_repo / tm.MANIFEST_REL
    assert manifest_path.is_file(), "scaffold must fingerprint the template"

    data = json.loads(manifest_path.read_text())
    assert data["template_version"] == tm.TEMPLATE_VERSION
    assert data["render_inputs"]["domain"] == DOMAIN
    assert data["render_inputs"]["product"] == PRODUCT
    assert data["files"], "manifest must record per-file hashes"


def test_manifest_tracks_governance_surface(meta_repo: Path):
    files = tm.read_manifest(meta_repo)["files"]
    for expected in ("AGENTS.md", "README.md", "Makefile",
                     ".platform/config/governance.yaml",
                     ".platform/config/skills.yaml"):
        assert expected in files, f"{expected} should be tracked template surface"


def test_manifest_excludes_per_domain_data(meta_repo: Path):
    """domain.yaml/repos.yaml are domain data — tracking them would produce
    permanent false drift (domain.yaml carries a created_at stamp)."""
    files = tm.read_manifest(meta_repo)["files"]
    assert ".platform/config/domain.yaml" not in files
    assert ".platform/config/repos.yaml" not in files
    assert tm.MANIFEST_REL not in files


def test_read_manifest_absent_returns_none(tmp_path: Path):
    assert tm.read_manifest(tmp_path) is None


def test_read_manifest_corrupt_returns_none(meta_repo: Path):
    (meta_repo / tm.MANIFEST_REL).write_text("{not json", encoding="utf-8")
    assert tm.read_manifest(meta_repo) is None


def test_is_tracked_filters_noise():
    assert tm.is_tracked("AGENTS.md")
    assert not tm.is_tracked(".platform/config/domain.yaml")
    assert not tm.is_tracked(".agents/skills/personas/dev/SKILL.md")
    assert not tm.is_tracked("docs/.DS_Store")
    assert not tm.is_tracked("docs/GOVERNANCE.md.orig")


# ── Classification ──────────────────────────────────────────────────────────

def test_fresh_scaffold_has_no_drift(meta_repo: Path):
    report = drift.classify(meta_repo, domain=DOMAIN)
    assert report.has_baseline is True
    assert report.drifted is False, f"unexpected drift: {report.counts}"
    assert report.counts == {drift.UNCHANGED: len(report.entries)}
    assert report.version_behind is False


def test_local_edit_is_locally_modified(meta_repo: Path):
    (meta_repo / "AGENTS.md").write_text("# locally rewritten\n", encoding="utf-8")

    report = drift.classify(meta_repo, domain=DOMAIN)
    entry = next(e for e in report.entries if e.path == "AGENTS.md")
    assert entry.status == drift.LOCALLY_MODIFIED
    assert entry.promotable is True
    assert entry.upgradable is False
    assert report.drifted is True


def test_new_local_file_is_local_only(meta_repo: Path):
    """The headline case: a skill added to the meta-repo post-generation."""
    skill = meta_repo / ".agents" / "skills" / "domain-triage" / "SKILL.md"
    skill.parent.mkdir(parents=True, exist_ok=True)
    skill.write_text("---\nname: domain-triage\n---\n", encoding="utf-8")

    report = drift.classify(meta_repo, domain=DOMAIN)
    entry = next(e for e in report.entries
                 if e.path == ".agents/skills/domain-triage/SKILL.md")
    assert entry.status == drift.LOCAL_ONLY
    assert entry in report.promotable


def test_template_update_is_fast_forwardable(meta_repo: Path, monkeypatch):
    """Template moved on, local copy untouched → safe to fast-forward."""
    original = meta_repo.joinpath("AGENTS.md").read_text(encoding="utf-8")

    def patched_agents_md(path: Path, domain: str) -> None:
        (path / "AGENTS.md").write_text(original + "\n## New template section\n",
                                        encoding="utf-8")

    monkeypatch.setattr("agentic_cli.meta_repo.scaffold._write_agents_md",
                        patched_agents_md)

    report = drift.classify(meta_repo, domain=DOMAIN)
    entry = next(e for e in report.entries if e.path == "AGENTS.md")
    assert entry.status == drift.TEMPLATE_UPDATED
    assert entry.upgradable is True
    assert entry in report.upgradable


def test_both_sides_changed_is_conflict(meta_repo: Path, monkeypatch):
    (meta_repo / "AGENTS.md").write_text("# local rewrite\n", encoding="utf-8")

    def patched_agents_md(path: Path, domain: str) -> None:
        (path / "AGENTS.md").write_text("# template rewrite\n", encoding="utf-8")

    monkeypatch.setattr("agentic_cli.meta_repo.scaffold._write_agents_md",
                        patched_agents_md)

    report = drift.classify(meta_repo, domain=DOMAIN)
    entry = next(e for e in report.entries if e.path == "AGENTS.md")
    assert entry.status == drift.BOTH_MODIFIED
    assert entry in report.conflicted
    assert entry.upgradable is False, "a conflict must never auto-apply"


def test_converged_edit_reports_unchanged(meta_repo: Path, monkeypatch):
    """A local edit that already matches the new template is not drift."""
    same = "# converged content\n"
    (meta_repo / "AGENTS.md").write_text(same, encoding="utf-8")

    monkeypatch.setattr(
        "agentic_cli.meta_repo.scaffold._write_agents_md",
        lambda path, domain: (path / "AGENTS.md").write_text(same, encoding="utf-8"))

    report = drift.classify(meta_repo, domain=DOMAIN)
    entry = next(e for e in report.entries if e.path == "AGENTS.md")
    assert entry.status == drift.UNCHANGED


def test_deleted_template_file_is_flagged(meta_repo: Path):
    (meta_repo / "AGENTS.md").unlink()

    report = drift.classify(meta_repo, domain=DOMAIN)
    entry = next(e for e in report.entries if e.path == "AGENTS.md")
    assert entry.status == drift.DELETED
    assert entry.upgradable is True, "upgrade should restore a deleted template file"


def test_missing_manifest_degrades_to_no_baseline(meta_repo: Path):
    """Meta-repos generated before manifests must still report usefully."""
    (meta_repo / tm.MANIFEST_REL).unlink()
    (meta_repo / "AGENTS.md").write_text("# edited\n", encoding="utf-8")

    report = drift.classify(meta_repo, domain=DOMAIN)
    assert report.has_baseline is False
    assert report.recorded_version is None

    entry = next(e for e in report.entries if e.path == "AGENTS.md")
    assert entry.status == drift.NO_BASELINE
    assert entry.upgradable is False, "never auto-apply without a baseline"
    # Files that happen to match the template are still correctly clean.
    assert any(e.status == drift.UNCHANGED for e in report.entries)


def test_no_baseline_falls_back_to_domain_yaml(meta_repo: Path):
    """Without a manifest, render inputs come from the domain's own config, so
    docs embedding the product name still compare equal."""
    (meta_repo / tm.MANIFEST_REL).unlink()

    report = drift.classify(meta_repo, domain=DOMAIN)
    assert report.domain == DOMAIN
    assert report.drifted is False, f"unexpected drift: {report.counts}"


def test_version_behind_detected(meta_repo: Path):
    manifest = json.loads((meta_repo / tm.MANIFEST_REL).read_text())
    manifest["template_version"] = "0.0.1"
    (meta_repo / tm.MANIFEST_REL).write_text(json.dumps(manifest), encoding="utf-8")

    report = drift.classify(meta_repo, domain=DOMAIN)
    assert report.recorded_version == "0.0.1"
    assert report.version_behind is True


def test_personas_are_not_drift(meta_repo: Path):
    """Persona skills are per-domain renders owned by `domain regen-personas`."""
    persona = meta_repo / ".agents" / "skills" / "personas" / "dev" / "SKILL.md"
    persona.parent.mkdir(parents=True, exist_ok=True)
    persona.write_text("---\nname: dev\n---\n", encoding="utf-8")

    report = drift.classify(meta_repo, domain=DOMAIN)
    assert all("personas/" not in e.path for e in report.entries)
    assert report.drifted is False


def test_submodule_checkouts_are_ignored(meta_repo: Path):
    """repos/ holds submodule checkouts — never template surface."""
    checkout = meta_repo / "repos" / "some-service" / "AGENTS.md"
    checkout.parent.mkdir(parents=True, exist_ok=True)
    checkout.write_text("# vendored\n", encoding="utf-8")

    report = drift.classify(meta_repo, domain=DOMAIN)
    assert all(not e.path.startswith("repos/") for e in report.entries)


def test_classify_rejects_non_meta_repo(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        drift.classify(tmp_path)


def test_classify_is_read_only(meta_repo: Path):
    before = tm.hash_surface(meta_repo)
    manifest_before = (meta_repo / tm.MANIFEST_REL).read_text()

    drift.classify(meta_repo, domain=DOMAIN)

    assert tm.hash_surface(meta_repo) == before
    assert (meta_repo / tm.MANIFEST_REL).read_text() == manifest_before


def test_report_to_dict_is_serializable(meta_repo: Path):
    (meta_repo / "AGENTS.md").write_text("# edited\n", encoding="utf-8")
    payload = drift.classify(meta_repo, domain=DOMAIN).to_dict()

    assert json.loads(json.dumps(payload))["drifted"] is True
    assert payload["current_version"] == tm.TEMPLATE_VERSION
    assert any(f["status"] == drift.LOCALLY_MODIFIED for f in payload["files"])
