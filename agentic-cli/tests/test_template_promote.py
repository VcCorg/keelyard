"""Tests for pushing a domain's local template improvements upstream (P3b).

Promotion is the risky direction: whatever lands in the overlay is rendered into
*every* future meta-repo. So the invariants under test are mostly refusals —

1. Tokenization must round-trip. A template that doesn't regenerate the file it
   came from would silently hand every other domain different content.
2. Domain-specific residue (emails, tickets, URLs, the domain's own words) must
   block a promotion unless a human explicitly overrides it.
3. Per-domain data files must never be promotable at all.
4. Dry run must write nothing.

And one end-to-end guarantee: a promoted file is picked up by a *different*
domain — first at scaffold time, then via `template upgrade`.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agentic_cli.meta_repo import template_drift as drift
from agentic_cli.meta_repo import template_manifest as tm
from agentic_cli.meta_repo import template_overlay as ov
from agentic_cli.meta_repo import template_promote as prom
from agentic_cli.meta_repo import template_upgrade as upg
from agentic_cli.meta_repo.scaffold import scaffold_domain_meta_repo

DOMAIN = "test-facility"
PRODUCT = "TESTPROD"
OWNER = "owner@example.com"
DESCRIPTION = "Test facility domain"


@pytest.fixture
def overlay(tmp_path: Path, monkeypatch) -> Path:
    """An isolated, git-backed overlay so tests never touch the real package."""
    root = tmp_path / "overlay"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=root, check=True)
    (root / ".keep").write_text("", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=root, check=True)
    monkeypatch.setenv(ov.OVERLAY_ENV, str(root))
    _INITIAL_BRANCH[root] = _current_branch(root)
    return root


#: The default branch name depends on the machine's git config, so record it.
_INITIAL_BRANCH: dict[Path, str] = {}


def _current_branch(repo: Path) -> str:
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
                          capture_output=True, text=True).stdout.strip()


def _scaffold(out: Path, domain: str = DOMAIN, product: str = PRODUCT) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    created = scaffold_domain_meta_repo(
        output_dir=out, domain=domain, product=product,
        description=DESCRIPTION, owner=OWNER,
        git_init=False, write_blueprint=False,
    )
    return created["root"]


@pytest.fixture
def meta_repo(tmp_path: Path, overlay: Path) -> Path:
    return _scaffold(tmp_path / "workspace")


# ── Overlay location ────────────────────────────────────────────────────────

def test_overlay_env_override_wins(tmp_path: Path, monkeypatch):
    monkeypatch.setenv(ov.OVERLAY_ENV, str(tmp_path / "elsewhere"))
    assert ov.overlay_root() == tmp_path / "elsewhere"


def test_default_overlay_is_in_tree(monkeypatch):
    monkeypatch.delenv(ov.OVERLAY_ENV, raising=False)
    assert ov.overlay_root().name == ov.OVERLAY_DIRNAME


def test_empty_overlay_lists_nothing_and_applies_nothing(overlay: Path, tmp_path: Path):
    """An overlay hosted in a git repo must not offer .git internals or its own
    bookkeeping files as template content."""
    assert ov.list_overlay(overlay) == []
    assert ov.apply_overlay(tmp_path, domain=DOMAIN) == []
    assert not (tmp_path / ".git").exists()


def test_missing_overlay_is_a_no_op(tmp_path: Path):
    assert ov.list_overlay(tmp_path / "nope") == []
    assert ov.apply_overlay(tmp_path, root=tmp_path / "nope") == []


# ── Tokenize / render ───────────────────────────────────────────────────────

def test_tokenize_replaces_render_inputs():
    body, subs, skipped = ov.tokenize(
        "Domain test-facility of TESTPROD, owner owner@example.com",
        domain=DOMAIN, product=PRODUCT, owner=OWNER, description="")

    assert "{{domain}}" in body and "{{product}}" in body and "{{owner}}" in body
    assert {s.placeholder for s in subs} == {"domain", "product", "owner"}
    assert skipped == []


def test_longer_value_is_tokenized_first():
    """product 'CWOW' is a substring of domain 'cwow-apoc' only case-insensitively,
    but a shorter value must never eat part of a longer one."""
    body, _, _ = ov.tokenize("alpha-beta and alpha",
                             domain="alpha-beta", product="alpha")
    assert body == "{{domain}} and {{product}}"


def test_short_values_are_not_substituted():
    body, subs, skipped = ov.tokenize("MTTR is a metric", product="MT")
    assert body == "MTTR is a metric"
    assert subs == []
    assert "product" in skipped


def test_word_boundaries_protect_substrings():
    body, _, _ = ov.tokenize("test-facilities and test-facility",
                             domain="test-facility")
    assert body == "test-facilities and {{domain}}"


def test_render_is_the_inverse_of_tokenize():
    original = f"# {DOMAIN}\n\nOwned by {OWNER} in {PRODUCT}.\n"
    body, _, _ = ov.tokenize(original, domain=DOMAIN, product=PRODUCT, owner=OWNER)
    assert ov.render(body, domain=DOMAIN, product=PRODUCT, owner=OWNER) == original


def test_render_leaves_literal_braces_alone():
    assert ov.render('{"a": 1} ${HOME}') == '{"a": 1} ${HOME}'


# ── Residual detection ──────────────────────────────────────────────────────

@pytest.mark.parametrize("content,kind", [
    ("See CWOW-12345 for context", "Jira-style issue key"),
    ("Ping alice@corp.com", "email address"),
    ("Docs at https://wiki.corp.com/x", "absolute URL"),
    ("Effective 2026-01-01", "date (would be frozen into the template)"),
])
def test_residual_patterns_are_flagged(content: str, kind: str):
    assert any(r.kind == kind for r in ov.find_residuals(content))


def test_domain_fragments_are_flagged():
    residuals = ov.find_residuals("the facility team owns this", domain="test-facility")
    assert any(r.kind == "domain fragment" and r.sample == "facility"
               for r in residuals)


def test_clean_generic_content_has_no_residuals():
    assert ov.find_residuals("# Engineering guardrails\n\nReview every change.\n",
                             domain=DOMAIN) == []


# ── Eligibility ─────────────────────────────────────────────────────────────

def test_only_promotable_drift_can_be_promoted(meta_repo: Path):
    with pytest.raises(ov.PromotionError, match="not promotable"):
        prom.promote(meta_repo, ["AGENTS.md"], domain=DOMAIN, dry_run=True)


def test_per_domain_data_is_never_promotable(meta_repo: Path):
    with pytest.raises(ov.PromotionError, match="per-domain data"):
        ov.plan_promotion(meta_repo, ".platform/config/domain.yaml",
                          drift.LOCALLY_MODIFIED, {"domain": DOMAIN})


def test_path_traversal_is_refused(meta_repo: Path):
    with pytest.raises(ov.PromotionError, match="Unsafe path"):
        ov.plan_promotion(meta_repo, "docs/../../etc/passwd",
                          drift.LOCAL_ONLY, {"domain": DOMAIN})


def test_promote_requires_at_least_one_path(meta_repo: Path):
    with pytest.raises(ov.PromotionError, match="No files given"):
        prom.promote(meta_repo, [], domain=DOMAIN, dry_run=True)


def test_locally_modified_file_is_discovered(meta_repo: Path):
    (meta_repo / "AGENTS.md").write_text("# sharpened guardrails\n", encoding="utf-8")

    entries, inputs = prom.promotable(meta_repo, domain=DOMAIN)

    assert "AGENTS.md" in {e.path for e in entries}
    assert inputs["domain"] == DOMAIN
    assert inputs["product"] == PRODUCT


def test_conflicted_files_are_not_offered_for_promotion(meta_repo: Path, monkeypatch):
    """Both sides moved: the template's change has to be reconciled first."""
    (meta_repo / "AGENTS.md").write_text("# local edit\n", encoding="utf-8")
    monkeypatch.setattr(
        "agentic_cli.meta_repo.scaffold._write_agents_md",
        lambda path, domain: (path / "AGENTS.md").write_text("# template edit\n",
                                                             encoding="utf-8"))

    entries, _ = prom.promotable(meta_repo, domain=DOMAIN)

    assert "AGENTS.md" not in {e.path for e in entries}


# ── Review gate ─────────────────────────────────────────────────────────────

def test_domain_specific_content_blocks_promotion(meta_repo: Path):
    (meta_repo / "AGENTS.md").write_text(
        "# Guardrails\n\nEscalate to alice@corp.com per CWOW-999.\n", encoding="utf-8")

    with pytest.raises(ov.PromotionError, match="domain-specific"):
        prom.promote(meta_repo, ["AGENTS.md"], domain=DOMAIN, dry_run=True)


def test_allow_unreviewed_overrides_the_gate(meta_repo: Path, overlay: Path):
    (meta_repo / "AGENTS.md").write_text(
        "# Guardrails\n\nEscalate to alice@corp.com.\n", encoding="utf-8")

    result = prom.promote(meta_repo, ["AGENTS.md"], domain=DOMAIN,
                          dry_run=True, allow_unreviewed=True)

    assert result.review_required == ["AGENTS.md"]
    assert result.plans[0].residuals


def test_clean_content_passes_the_gate(meta_repo: Path):
    (meta_repo / "docs" / "PLAYBOOK.md").write_text(
        "# Playbook\n\nReview every change before merge.\n", encoding="utf-8")

    result = prom.promote(meta_repo, ["docs/PLAYBOOK.md"], domain=DOMAIN,
                          dry_run=True)

    assert result.plans[0].residuals == []


def test_a_file_with_nothing_to_tokenize_is_flagged_for_review(meta_repo: Path):
    """Zero substitutions is legitimate for generic guidance, but it can equally
    mean the tokenizer found nothing it recognized — so a human confirms."""
    (meta_repo / "docs" / "PLAYBOOK.md").write_text(
        "# Playbook\n\nReview every change before merge.\n", encoding="utf-8")

    result = prom.promote(meta_repo, ["docs/PLAYBOOK.md"], domain=DOMAIN,
                          dry_run=True)

    assert result.plans[0].substitutions == []
    assert result.review_required == ["docs/PLAYBOOK.md"]


# ── Dry run ─────────────────────────────────────────────────────────────────

def test_dry_run_writes_nothing(meta_repo: Path, overlay: Path):
    (meta_repo / "docs" / "PLAYBOOK.md").write_text(
        "# Playbook\n\nReview every change.\n", encoding="utf-8")
    before_overlay = ov.list_overlay(overlay)
    before_repo = tm.hash_surface(meta_repo)

    result = prom.promote(meta_repo, ["docs/PLAYBOOK.md"], domain=DOMAIN,
                          dry_run=True)

    assert result.dry_run is True
    assert result.written == []
    assert ov.list_overlay(overlay) == before_overlay
    assert tm.hash_surface(meta_repo) == before_repo
    assert result.plans[0].content  # the tokenized body is still available to review


# ── Apply ───────────────────────────────────────────────────────────────────

def test_promotion_writes_a_tokenized_overlay_file(meta_repo: Path, overlay: Path):
    (meta_repo / "docs" / "PLAYBOOK.md").write_text(
        f"# {PRODUCT} playbook\n\nReview every change.\n", encoding="utf-8")

    result = prom.promote(meta_repo, ["docs/PLAYBOOK.md"], domain=DOMAIN)

    assert result.written == ["docs/PLAYBOOK.md"]
    body = (overlay / "docs/PLAYBOOK.md").read_text()
    assert body == "# {{product}} playbook\n\nReview every change.\n"


def test_promotion_commits_on_a_branch_without_pushing(meta_repo: Path, overlay: Path):
    (meta_repo / "docs" / "PLAYBOOK.md").write_text("# Playbook\n", encoding="utf-8")

    result = prom.promote(meta_repo, ["docs/PLAYBOOK.md"], domain=DOMAIN)

    assert result.branch == "template-promote/test-facility/docs-PLAYBOOK.md"
    assert result.committed is True and result.commit
    assert result.pushed is False
    assert "push -u origin" in result.push_hint
    assert _current_branch(overlay) == result.branch


def test_no_commit_leaves_the_overlay_repo_untouched(meta_repo: Path, overlay: Path):
    (meta_repo / "docs" / "PLAYBOOK.md").write_text("# Playbook\n", encoding="utf-8")

    result = prom.promote(meta_repo, ["docs/PLAYBOOK.md"], domain=DOMAIN,
                          commit=False)

    assert result.committed is False and result.branch == ""
    assert (overlay / "docs/PLAYBOOK.md").is_file()
    assert _current_branch(overlay) == _INITIAL_BRANCH[overlay]
    status = subprocess.run(["git", "-C", str(overlay), "status", "--porcelain",
                             "--untracked-files=all"],
                            capture_output=True, text=True).stdout
    assert "docs/PLAYBOOK.md" in status  # left uncommitted for review


def test_overlay_outside_a_git_repo_still_promotes(meta_repo: Path, tmp_path: Path,
                                                  monkeypatch):
    plain = tmp_path / "plain-overlay"
    monkeypatch.setenv(ov.OVERLAY_ENV, str(plain))
    (meta_repo / "docs" / "PLAYBOOK.md").write_text("# Playbook\n", encoding="utf-8")

    result = prom.promote(meta_repo, ["docs/PLAYBOOK.md"], domain=DOMAIN)

    assert (plain / "docs/PLAYBOOK.md").is_file()
    assert result.committed is False
    assert "not inside a git repository" in result.push_hint


def test_a_second_revision_of_the_same_file_can_be_promoted(meta_repo: Path,
                                                            overlay: Path):
    """Once promoted, the file IS the template. A later local edit must therefore
    become `locally-modified` again — which only holds because promotion advanced
    the source repo's baseline."""
    (meta_repo / "docs" / "PLAYBOOK.md").write_text("# v1\n", encoding="utf-8")
    first = prom.promote(meta_repo, ["docs/PLAYBOOK.md"], domain=DOMAIN)
    assert first.rebaselined == ["docs/PLAYBOOK.md"]

    (meta_repo / "docs" / "PLAYBOOK.md").write_text("# v2\n", encoding="utf-8")
    entries, _ = prom.promotable(meta_repo, domain=DOMAIN)
    assert next(e for e in entries if e.path == "docs/PLAYBOOK.md").status == \
        drift.LOCALLY_MODIFIED

    result = prom.promote(meta_repo, ["docs/PLAYBOOK.md"], domain=DOMAIN)

    assert result.plans[0].replaces_existing is True
    assert (overlay / "docs/PLAYBOOK.md").read_text() == "# v2\n"


def test_the_promoting_domain_stops_reporting_its_own_contribution_as_drift(
        meta_repo: Path, overlay: Path):
    (meta_repo / "docs" / "PLAYBOOK.md").write_text("# Playbook\n", encoding="utf-8")

    prom.promote(meta_repo, ["docs/PLAYBOOK.md"], domain=DOMAIN)

    report = drift.classify(meta_repo, domain=DOMAIN)
    entry = next(e for e in report.entries if e.path == "docs/PLAYBOOK.md")
    assert entry.status == drift.UNCHANGED


def test_rebaselining_touches_only_the_promoted_paths(meta_repo: Path, overlay: Path):
    before = dict((tm.read_manifest(meta_repo) or {}).get("files") or {})
    (meta_repo / "docs" / "PLAYBOOK.md").write_text("# Playbook\n", encoding="utf-8")

    prom.promote(meta_repo, ["docs/PLAYBOOK.md"], domain=DOMAIN)

    after = dict((tm.read_manifest(meta_repo) or {}).get("files") or {})
    assert set(after) - set(before) == {"docs/PLAYBOOK.md"}
    assert {k: v for k, v in after.items() if k in before} == before


def test_branch_name_collapses_multiple_files():
    assert prom.branch_name("test-facility", ["a.md", "b.md"]) == \
        "template-promote/test-facility/2-files"


def test_branch_name_sanitizes_components():
    name = prom.branch_name("weird domain!", ["docs/x y.md"])
    assert name == "template-promote/weird-domain/docs-x-y.md"
    assert subprocess.run(["git", "check-ref-format", "--branch", name],
                          capture_output=True).returncode == 0


# ── Round trip safety ───────────────────────────────────────────────────────

def test_promotion_is_refused_when_tokenization_cannot_round_trip(
        meta_repo: Path, monkeypatch):
    """If the tokenized body would render back to something else, publishing it
    hands every other domain content its own author never wrote."""
    (meta_repo / "docs" / "PLAYBOOK.md").write_text("# Playbook\n", encoding="utf-8")
    monkeypatch.setattr(ov, "tokenize",
                        lambda content, **kw: ("# corrupted\n", [], []))

    with pytest.raises(ov.PromotionError, match="round-trip"):
        prom.promote(meta_repo, ["docs/PLAYBOOK.md"], domain=DOMAIN, dry_run=True)


def test_a_file_naming_the_domain_round_trips(meta_repo: Path, overlay: Path):
    original = f"# {DOMAIN} playbook\n\nOwned by the {PRODUCT} team.\n"
    (meta_repo / "docs" / "PLAYBOOK.md").write_text(original, encoding="utf-8")

    result = prom.promote(meta_repo, ["docs/PLAYBOOK.md"], domain=DOMAIN,
                          allow_unreviewed=True)

    rendered = ov.render((overlay / "docs/PLAYBOOK.md").read_text(),
                         domain=DOMAIN, product=PRODUCT,
                         description=DESCRIPTION, owner=OWNER)
    assert rendered == original
    assert result.written == ["docs/PLAYBOOK.md"]


# ── The point of it all: another domain receives the improvement ────────────

def test_a_promoted_file_reaches_a_brand_new_domain(meta_repo: Path, overlay: Path,
                                                    tmp_path: Path):
    (meta_repo / "docs" / "PLAYBOOK.md").write_text(
        f"# {PRODUCT} playbook\n\nReview every change.\n", encoding="utf-8")
    prom.promote(meta_repo, ["docs/PLAYBOOK.md"], domain=DOMAIN)

    other = _scaffold(tmp_path / "other-ws", domain="other-domain", product="OTHER")

    assert (other / "docs/PLAYBOOK.md").read_text() == \
        "# OTHER playbook\n\nReview every change.\n"


def test_a_new_domain_records_overlay_content_in_its_baseline(
        meta_repo: Path, overlay: Path, tmp_path: Path):
    """The overlay is applied before the manifest, so a fresh repo is in sync —
    otherwise every new domain would be born reporting drift."""
    (meta_repo / "docs" / "PLAYBOOK.md").write_text("# Playbook\n", encoding="utf-8")
    prom.promote(meta_repo, ["docs/PLAYBOOK.md"], domain=DOMAIN)

    other = _scaffold(tmp_path / "other-ws", domain="other-domain", product="OTHER")
    report = drift.classify(other, domain="other-domain")

    entry = next(e for e in report.entries if e.path == "docs/PLAYBOOK.md")
    assert entry.status == drift.UNCHANGED


def test_an_existing_domain_upgrades_into_the_promoted_file(
        meta_repo: Path, overlay: Path, tmp_path: Path):
    """The full loop: domain A promotes, domain B fast-forwards."""
    existing = _scaffold(tmp_path / "b-ws", domain="b-domain", product="BEE")
    (meta_repo / "docs" / "PLAYBOOK.md").write_text(
        f"# {PRODUCT} playbook\n\nReview every change.\n", encoding="utf-8")
    prom.promote(meta_repo, ["docs/PLAYBOOK.md"], domain=DOMAIN)

    result = upg.upgrade(existing, domain="b-domain", dry_run=False)

    assert (existing / "docs/PLAYBOOK.md").read_text() == \
        "# BEE playbook\n\nReview every change.\n"
    action = next(a for a in result.actions if a.path == "docs/PLAYBOOK.md")
    assert action.action in {upg.UPDATED, upg.RESTORED}


def test_promoting_does_not_alter_the_source_repo_content(meta_repo: Path,
                                                          overlay: Path):
    """Promotion copies content upstream; it must never rewrite the domain's own
    files. Only the baseline manifest (excluded from the tracked surface) moves."""
    (meta_repo / "docs" / "PLAYBOOK.md").write_text("# Playbook\n", encoding="utf-8")
    before = tm.hash_surface(meta_repo)

    prom.promote(meta_repo, ["docs/PLAYBOOK.md"], domain=DOMAIN)

    assert tm.hash_surface(meta_repo) == before


# ── Resolution by domain name ───────────────────────────────────────────────

def test_promote_domain_reports_a_missing_meta_repo(monkeypatch):
    monkeypatch.setattr(
        "agentic_cli.meta_repo.detector.detect_domain_meta_repo",
        lambda *a, **k: None)
    with pytest.raises(FileNotFoundError, match="No meta-repo found"):
        prom.promote_domain("ghost", ["AGENTS.md"])
