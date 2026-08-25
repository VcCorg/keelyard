"""Tests for applying template updates to an existing meta-repo (phase 2).

Two invariants dominate, because getting either wrong destroys a team's work:

1. Only files untouched since generation may be overwritten. Local edits,
   domain-authored files and both-sides conflicts must survive an upgrade.
2. Re-baselining must not advance a locally-modified file's baseline, or the
   NEXT upgrade would classify it as `template-updated` and silently overwrite
   the local edit.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from agentic_cli.meta_repo import template_drift as drift
from agentic_cli.meta_repo import template_manifest as tm
from agentic_cli.meta_repo import template_upgrade as upg
from agentic_cli.meta_repo.scaffold import scaffold_domain_meta_repo

DOMAIN = "test-facility"
PRODUCT = "TEST"


@pytest.fixture
def meta_repo(tmp_path: Path) -> Path:
    out = tmp_path / "workspace"
    out.mkdir()
    created = scaffold_domain_meta_repo(
        output_dir=out, domain=DOMAIN, product=PRODUCT,
        description="Test domain", owner="owner@example.com",
        git_init=False, write_blueprint=False,
    )
    repo = created["root"]
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    return repo


def _patch_agents_md(monkeypatch, content: str) -> None:
    """Make the template render a different AGENTS.md."""
    monkeypatch.setattr(
        "agentic_cli.meta_repo.scaffold._write_agents_md",
        lambda path, domain: (path / "AGENTS.md").write_text(content, encoding="utf-8"))


def _action_for(result: upg.UpgradeReport, path: str) -> upg.FileAction:
    return next(a for a in result.actions if a.path == path)


# ── Nothing to do ───────────────────────────────────────────────────────────

def test_in_sync_repo_needs_no_upgrade(meta_repo: Path):
    result = upg.upgrade(meta_repo, domain=DOMAIN, dry_run=True)
    assert result.changed == 0
    assert result.actions == []


def test_rejects_non_meta_repo(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        upg.upgrade(tmp_path)


# ── Fast-forward ────────────────────────────────────────────────────────────

def test_template_update_is_applied(meta_repo: Path, monkeypatch):
    _patch_agents_md(monkeypatch, "# new template AGENTS\n")

    result = upg.upgrade(meta_repo, domain=DOMAIN, dry_run=False)

    assert (meta_repo / "AGENTS.md").read_text() == "# new template AGENTS\n"
    assert _action_for(result, "AGENTS.md").action == upg.UPDATED
    assert result.changed == 1


def test_dry_run_writes_nothing(meta_repo: Path, monkeypatch):
    _patch_agents_md(monkeypatch, "# new template AGENTS\n")
    before = tm.hash_surface(meta_repo)

    result = upg.upgrade(meta_repo, domain=DOMAIN, dry_run=True)

    assert tm.hash_surface(meta_repo) == before
    assert result.manifest_written is False
    assert _action_for(result, "AGENTS.md").action == upg.UPDATED


def test_deleted_file_is_restored(meta_repo: Path):
    (meta_repo / "AGENTS.md").unlink()

    result = upg.upgrade(meta_repo, domain=DOMAIN, dry_run=False)

    assert (meta_repo / "AGENTS.md").is_file()
    assert _action_for(result, "AGENTS.md").action == upg.RESTORED


def test_upgrade_leaves_repo_in_sync(meta_repo: Path, monkeypatch):
    _patch_agents_md(monkeypatch, "# new template AGENTS\n")

    upg.upgrade(meta_repo, domain=DOMAIN, dry_run=False)

    assert drift.classify(meta_repo, domain=DOMAIN).drifted is False


# ── Local work must survive ─────────────────────────────────────────────────

def test_local_edit_is_never_overwritten(meta_repo: Path):
    edited = "# our own governance rules\n"
    (meta_repo / "AGENTS.md").write_text(edited, encoding="utf-8")

    result = upg.upgrade(meta_repo, domain=DOMAIN, dry_run=False)

    assert (meta_repo / "AGENTS.md").read_text() == edited
    action = _action_for(result, "AGENTS.md")
    assert action.action == upg.SKIPPED
    assert action.status == drift.LOCALLY_MODIFIED


def test_local_only_file_is_never_touched(meta_repo: Path):
    skill = meta_repo / ".agents" / "skills" / "domain-triage" / "SKILL.md"
    skill.parent.mkdir(parents=True, exist_ok=True)
    skill.write_text("---\nname: domain-triage\n---\n", encoding="utf-8")

    upg.upgrade(meta_repo, domain=DOMAIN, dry_run=False)

    assert skill.is_file()


def test_conflict_is_preserved_with_a_sidecar(meta_repo: Path, monkeypatch):
    (meta_repo / "AGENTS.md").write_text("# local\n", encoding="utf-8")
    _patch_agents_md(monkeypatch, "# template\n")

    result = upg.upgrade(meta_repo, domain=DOMAIN, dry_run=False)

    assert (meta_repo / "AGENTS.md").read_text() == "# local\n", "local wins"
    assert (meta_repo / "AGENTS.md.new").read_text() == "# template\n"
    action = _action_for(result, "AGENTS.md")
    assert action.action == upg.CONFLICT
    assert action.sidecar == "AGENTS.md.new"
    assert result.changed == 0, "a conflict is not a change"


def test_conflict_sidecars_can_be_disabled(meta_repo: Path, monkeypatch):
    (meta_repo / "AGENTS.md").write_text("# local\n", encoding="utf-8")
    _patch_agents_md(monkeypatch, "# template\n")

    upg.upgrade(meta_repo, domain=DOMAIN, dry_run=False, write_conflicts=False)

    assert not (meta_repo / "AGENTS.md.new").exists()


def test_sidecars_are_not_themselves_tracked(meta_repo: Path, monkeypatch):
    """A .new sidecar must not show up as drift on the next run."""
    (meta_repo / "AGENTS.md").write_text("# local\n", encoding="utf-8")
    _patch_agents_md(monkeypatch, "# template\n")
    upg.upgrade(meta_repo, domain=DOMAIN, dry_run=False)

    paths = {e.path for e in drift.classify(meta_repo, domain=DOMAIN).entries}
    assert "AGENTS.md.new" not in paths


def test_no_baseline_repo_is_treated_as_conflict(meta_repo: Path):
    """Without a baseline we cannot prove a file is unedited, so never overwrite."""
    (meta_repo / tm.MANIFEST_REL).unlink()
    (meta_repo / "AGENTS.md").write_text("# edited\n", encoding="utf-8")

    result = upg.upgrade(meta_repo, domain=DOMAIN, dry_run=False)

    assert (meta_repo / "AGENTS.md").read_text() == "# edited\n"
    action = _action_for(result, "AGENTS.md")
    assert action.action == upg.CONFLICT
    assert action.status == drift.NO_BASELINE


# ── Re-baselining (the subtle one) ───────────────────────────────────────────

def test_rebaseline_preserves_local_edits_across_two_upgrades(meta_repo: Path):
    """Regression: a naive "rewrite the manifest from disk" would record the
    edited hash as the baseline, so the SECOND upgrade would see
    `template-updated` and overwrite the local edit."""
    edited = "# our own governance rules\n"
    (meta_repo / "AGENTS.md").write_text(edited, encoding="utf-8")

    upg.upgrade(meta_repo, domain=DOMAIN, dry_run=False)
    second = upg.upgrade(meta_repo, domain=DOMAIN, dry_run=False)

    assert (meta_repo / "AGENTS.md").read_text() == edited
    assert _action_for(second, "AGENTS.md").status == drift.LOCALLY_MODIFIED


def test_rebaseline_keeps_conflicts_flagged(meta_repo: Path, monkeypatch):
    (meta_repo / "AGENTS.md").write_text("# local\n", encoding="utf-8")
    _patch_agents_md(monkeypatch, "# template\n")

    upg.upgrade(meta_repo, domain=DOMAIN, dry_run=False)
    second = upg.upgrade(meta_repo, domain=DOMAIN, dry_run=False)

    assert _action_for(second, "AGENTS.md").action == upg.CONFLICT, \
        "an unresolved conflict must stay a conflict"


def test_upgrade_bumps_the_recorded_version(meta_repo: Path):
    manifest = json.loads((meta_repo / tm.MANIFEST_REL).read_text())
    manifest["template_version"] = "0.0.1"
    (meta_repo / tm.MANIFEST_REL).write_text(json.dumps(manifest))

    result = upg.upgrade(meta_repo, domain=DOMAIN, dry_run=False)

    after = json.loads((meta_repo / tm.MANIFEST_REL).read_text())
    assert result.from_version == "0.0.1"
    assert after["template_version"] == tm.TEMPLATE_VERSION
    assert after["upgraded_from"] == "0.0.1"
    assert "upgraded_at" in after


def test_rebaseline_preserves_render_inputs(meta_repo: Path, monkeypatch):
    _patch_agents_md(monkeypatch, "# new\n")

    upg.upgrade(meta_repo, domain=DOMAIN, dry_run=False)

    after = json.loads((meta_repo / tm.MANIFEST_REL).read_text())
    assert after["render_inputs"]["domain"] == DOMAIN
    assert after["render_inputs"]["product"] == PRODUCT


# ── Prune ───────────────────────────────────────────────────────────────────

def test_template_removed_is_kept_by_default(meta_repo: Path):
    """Deleting a team's file is never the safe default."""
    manifest = json.loads((meta_repo / tm.MANIFEST_REL).read_text())
    extra = meta_repo / "docs" / "LEGACY.md"
    extra.write_text("# legacy\n", encoding="utf-8")
    manifest["files"]["docs/LEGACY.md"] = tm.sha256_file(extra)
    (meta_repo / tm.MANIFEST_REL).write_text(json.dumps(manifest))

    result = upg.upgrade(meta_repo, domain=DOMAIN, dry_run=False)

    assert extra.is_file()
    action = _action_for(result, "docs/LEGACY.md")
    assert action.action == upg.SKIPPED
    assert "--prune" in action.detail


def test_prune_removes_dropped_template_files(meta_repo: Path):
    manifest = json.loads((meta_repo / tm.MANIFEST_REL).read_text())
    extra = meta_repo / "docs" / "LEGACY.md"
    extra.write_text("# legacy\n", encoding="utf-8")
    manifest["files"]["docs/LEGACY.md"] = tm.sha256_file(extra)
    (meta_repo / tm.MANIFEST_REL).write_text(json.dumps(manifest))

    result = upg.upgrade(meta_repo, domain=DOMAIN, dry_run=False, prune=True)

    assert not extra.exists()
    assert _action_for(result, "docs/LEGACY.md").action == upg.PRUNED


# ── Git safety net ──────────────────────────────────────────────────────────

def test_uncommitted_file_is_not_overwritten(meta_repo: Path, monkeypatch):
    """A tracked-but-unmodified file can be restored with git; uncommitted work
    cannot — so it is skipped unless forced."""
    # Same content as the baseline in git terms? No: make it dirty but keep the
    # drift status at `template-updated` by committing the edit as the baseline.
    (meta_repo / "AGENTS.md").write_text("# baseline\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=meta_repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "b"], cwd=meta_repo, check=True)
    manifest = json.loads((meta_repo / tm.MANIFEST_REL).read_text())
    manifest["files"]["AGENTS.md"] = tm.sha256_file(meta_repo / "AGENTS.md")
    (meta_repo / tm.MANIFEST_REL).write_text(json.dumps(manifest))
    # Now dirty it without committing, and keep the manifest baseline in step so
    # the classifier still says `template-updated`.
    (meta_repo / "AGENTS.md").write_text("# uncommitted work\n", encoding="utf-8")
    manifest["files"]["AGENTS.md"] = tm.sha256_file(meta_repo / "AGENTS.md")
    (meta_repo / tm.MANIFEST_REL).write_text(json.dumps(manifest))
    _patch_agents_md(monkeypatch, "# template\n")

    result = upg.upgrade(meta_repo, domain=DOMAIN, dry_run=False)

    assert (meta_repo / "AGENTS.md").read_text() == "# uncommitted work\n"
    action = _action_for(result, "AGENTS.md")
    assert action.action == upg.SKIPPED
    assert "--force" in action.detail


def test_force_overwrites_uncommitted_file(meta_repo: Path, monkeypatch):
    (meta_repo / "AGENTS.md").write_text("# uncommitted work\n", encoding="utf-8")
    manifest = json.loads((meta_repo / tm.MANIFEST_REL).read_text())
    manifest["files"]["AGENTS.md"] = tm.sha256_file(meta_repo / "AGENTS.md")
    (meta_repo / tm.MANIFEST_REL).write_text(json.dumps(manifest))
    _patch_agents_md(monkeypatch, "# template\n")

    result = upg.upgrade(meta_repo, domain=DOMAIN, dry_run=False, force=True)

    assert (meta_repo / "AGENTS.md").read_text() == "# template\n"
    assert _action_for(result, "AGENTS.md").action == upg.UPDATED


def test_non_git_repo_is_flagged_as_unprotected(tmp_path: Path, monkeypatch):
    out = tmp_path / "ws"
    out.mkdir()
    repo = scaffold_domain_meta_repo(
        output_dir=out, domain=DOMAIN, product=PRODUCT,
        git_init=False, write_blueprint=False)["root"]
    _patch_agents_md(monkeypatch, "# new\n")

    result = upg.upgrade(repo, domain=DOMAIN, dry_run=True)

    assert any("not a git repository" in w for w in result.blocked)


def test_uncommitted_paths_empty_without_git(tmp_path: Path):
    assert upg.uncommitted_paths(tmp_path, ["AGENTS.md"]) == set()


# ── Reporting ───────────────────────────────────────────────────────────────

def test_report_serializes(meta_repo: Path, monkeypatch):
    _patch_agents_md(monkeypatch, "# new\n")
    payload = upg.upgrade(meta_repo, domain=DOMAIN, dry_run=True).to_dict()

    assert json.loads(json.dumps(payload))["dry_run"] is True
    assert payload["counts"][upg.UPDATED] == 1


def test_upgrade_domain_missing_repo_raises():
    with pytest.raises(FileNotFoundError, match="No meta-repo found"):
        upg.upgrade_domain("definitely-not-a-real-domain-xyz")
