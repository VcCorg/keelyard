"""Tests for domain → registry skill promotion (phase 3).

The origin classifier is the safety-critical part: promoting an injected
superpowers baseline is pointless, and promoting a platform-generated
domain-context skill would publish one domain's private context to every other
domain. Both are pinned here.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from agentic_cli import skills_upstream as up

DOMAIN = "cwow-widget"


def _write_skill(root: Path, name: str, body: str = "Guidance body.",
                 description: str = "Does a useful thing") -> Path:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\ntags: [alpha, beta]\n---\n\n"
        f"# {name}\n\n{body}\n",
        encoding="utf-8",
    )
    return d


@pytest.fixture
def domain_repo(tmp_path: Path) -> Path:
    """A domain context-meta repo with a realistic mix of skill origins."""
    repo = tmp_path / "cwow-widget-context-meta"
    (repo / ".platform" / "config").mkdir(parents=True)
    skills = repo / ".skills"
    skills.mkdir()

    _write_skill(skills, "brainstorming")                 # injected baseline
    _write_skill(skills, "widget-triage")                 # domain authored
    _write_skill(skills, "systematic-debugging-cwow-widget")  # forked
    _write_skill(skills, "project-context")               # platform generated
    _write_skill(skills, "cwow-widget-domain-skill")      # platform generated

    manifest = {
        "domain": DOMAIN,
        "skills": {
            "brainstorming": {"source": "superpowers", "status": "injected",
                              "customized": False},
            "systematic-debugging-cwow-widget": {
                "source": "superpowers", "status": "forked", "customized": True,
                "upstream_skill": "systematic-debugging"},
        },
    }
    (repo / ".domain").mkdir()
    (repo / ".domain" / "skills-manifest.json").write_text(json.dumps(manifest))
    return repo


@pytest.fixture
def registry(tmp_path: Path) -> Path:
    """A git-backed skills registry with one existing skill."""
    reg = tmp_path / "skills-registry"
    (reg / "skills").mkdir(parents=True)
    (reg / "registry.json").write_text(json.dumps({
        "version": "1.0",
        "skills": [{"name": "java-spring-boot", "description": "Spring",
                    "tags": ["java"], "auto_detect": {"files": ["pom.xml"]}}],
    }, indent=2))
    _write_skill(reg / "skills", "java-spring-boot", description="Spring")

    subprocess.run(["git", "init", "-q"], cwd=reg, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=reg, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=reg, check=True)
    subprocess.run(["git", "add", "-A"], cwd=reg, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=reg, check=True)
    return reg


def _by_name(candidates) -> dict[str, up.SkillCandidate]:
    return {c.name: c for c in candidates}


# ── Origin classification ───────────────────────────────────────────────────

def test_injected_baseline_is_not_promotable(domain_repo: Path):
    c = _by_name(up.discover_domain_skills(domain_repo))["brainstorming"]
    assert c.origin == up.UPSTREAM_BASELINE
    assert c.promotable is False
    assert "already upstream" in c.reason


def test_domain_authored_is_promotable(domain_repo: Path):
    c = _by_name(up.discover_domain_skills(domain_repo))["widget-triage"]
    assert c.origin == up.DOMAIN_AUTHORED
    assert c.kind == up.NEW
    assert c.promotable is True
    assert c.description == "Does a useful thing"


def test_forked_skill_is_promotable_as_customized(domain_repo: Path):
    """A fork is recorded with source=superpowers, so the customization check
    must win over the baseline check or forks would look like untouched
    upstream content."""
    c = _by_name(up.discover_domain_skills(domain_repo))[
        "systematic-debugging-cwow-widget"]
    assert c.origin == up.DOMAIN_CUSTOMIZED
    assert c.upstream_skill == "systematic-debugging"
    assert c.promotable is True


@pytest.mark.parametrize("name", ["project-context", "cwow-widget-domain-skill"])
def test_platform_generated_is_not_promotable(domain_repo: Path, name: str):
    """These render a single domain's data — publishing them would leak that
    domain's context into every other domain."""
    c = _by_name(up.discover_domain_skills(domain_repo))[name]
    assert c.origin == up.PLATFORM_GENERATED
    assert c.promotable is False
    assert "not reusable" in c.reason


def test_registry_installed_skills_are_not_promotable(domain_repo: Path):
    validated = domain_repo / "skills" / "validated"
    validated.mkdir(parents=True)
    _write_skill(validated, "python-fastapi")

    c = _by_name(up.discover_domain_skills(domain_repo))["python-fastapi"]
    assert c.origin == up.REGISTRY_SOURCED
    assert c.promotable is False


def test_personas_and_superpowers_dirs_are_skipped(domain_repo: Path):
    _write_skill(domain_repo / ".agents" / "skills" / "personas", "dev")
    _write_skill(domain_repo / ".skills" / "superpowers" / "skills", "writing-plans")

    names = {c.name for c in up.discover_domain_skills(domain_repo)}
    assert "dev" not in names
    assert "writing-plans" not in names


def test_agents_skills_dir_is_discovered(domain_repo: Path):
    _write_skill(domain_repo / ".agents" / "skills", "widget-agent-helper")

    c = _by_name(up.discover_domain_skills(domain_repo))["widget-agent-helper"]
    assert c.location == ".agents/skills"
    assert c.promotable is True


def test_dirs_without_skill_md_are_ignored(domain_repo: Path):
    (domain_repo / ".skills" / "not-a-skill").mkdir()
    names = {c.name for c in up.discover_domain_skills(domain_repo)}
    assert "not-a-skill" not in names


# ── Kind vs the registry ────────────────────────────────────────────────────

def test_identical_registry_skill_is_not_promotable(domain_repo: Path, registry: Path):
    """Re-promoting unchanged content must be a no-op, not a churn commit."""
    _write_skill(domain_repo / ".skills", "java-spring-boot", description="Spring")

    c = _by_name(up.discover_domain_skills(domain_repo, registry=registry))[
        "java-spring-boot"]
    assert c.kind == up.IDENTICAL
    assert c.promotable is False


def test_changed_registry_skill_is_an_update(domain_repo: Path, registry: Path):
    _write_skill(domain_repo / ".skills", "java-spring-boot",
                 body="Domain-improved guidance.", description="Spring")

    c = _by_name(up.discover_domain_skills(domain_repo, registry=registry))[
        "java-spring-boot"]
    assert c.kind == up.UPDATE
    assert c.promotable is True


# ── Gate ────────────────────────────────────────────────────────────────────

def test_gate_rejects_missing_frontmatter(tmp_path: Path):
    d = tmp_path / "bad"
    d.mkdir()
    (d / "SKILL.md").write_text("# no frontmatter\n", encoding="utf-8")

    passed, notes = up.default_gate(d)
    assert passed is False
    assert any("frontmatter" in n for n in notes)


def test_gate_rejects_missing_skill_md(tmp_path: Path):
    d = tmp_path / "empty"
    d.mkdir()
    passed, notes = up.default_gate(d)
    assert passed is False
    assert notes == ["SKILL.md is missing"]


def test_gate_accepts_well_formed_skill(tmp_path: Path):
    d = _write_skill(tmp_path, "fine")
    passed, notes = up.default_gate(d)
    assert passed is True
    assert any("structure ok" in n for n in notes)


def test_promote_runs_the_gate_and_refuses_failures(domain_repo: Path, registry: Path):
    bad = domain_repo / ".skills" / "widget-triage" / "SKILL.md"
    bad.write_text("no frontmatter at all\n", encoding="utf-8")
    c = _by_name(up.discover_domain_skills(domain_repo, registry=registry))[
        "widget-triage"]

    with pytest.raises(up.PromotionError, match="gate"):
        up.promote_to_registry(c, DOMAIN, registry, domain_repo=domain_repo)

    assert not (registry / "skills" / "widget-triage").exists()


def test_failing_gate_leaves_an_existing_registry_copy_intact(
    domain_repo: Path, registry: Path
):
    """Regression: the gate must run BEFORE anything is written. An earlier
    design staged the skill into the registry to score it, which destroyed the
    curated upstream copy whenever the gate then failed."""
    _write_skill(domain_repo / ".skills", "java-spring-boot",
                 body="Improved.", description="Spring Boot, improved")
    c = _by_name(up.discover_domain_skills(domain_repo, registry=registry))[
        "java-spring-boot"]
    before_tree = up.tree_hash(registry / "skills" / "java-spring-boot")
    before_json = (registry / "registry.json").read_text()

    with pytest.raises(up.PromotionError):
        up.promote_to_registry(c, DOMAIN, registry, domain_repo=domain_repo,
                               gate=lambda p: (False, ["nope"]))

    assert up.tree_hash(registry / "skills" / "java-spring-boot") == before_tree
    assert (registry / "registry.json").read_text() == before_json


def test_dry_run_does_not_touch_an_existing_registry_copy(
    domain_repo: Path, registry: Path
):
    _write_skill(domain_repo / ".skills", "java-spring-boot",
                 body="Improved.", description="Spring Boot, improved")
    c = _by_name(up.discover_domain_skills(domain_repo, registry=registry))[
        "java-spring-boot"]
    before_tree = up.tree_hash(registry / "skills" / "java-spring-boot")

    up.promote_to_registry(c, DOMAIN, registry, domain_repo=domain_repo,
                           dry_run=True)

    assert up.tree_hash(registry / "skills" / "java-spring-boot") == before_tree


def test_custom_gate_is_honoured(domain_repo: Path, registry: Path):
    """The dashboard passes its full trial scorecard here."""
    c = _by_name(up.discover_domain_skills(domain_repo, registry=registry))[
        "widget-triage"]

    with pytest.raises(up.PromotionError, match="scorecard said no"):
        up.promote_to_registry(c, DOMAIN, registry, domain_repo=domain_repo,
                               gate=lambda p: (False, ["scorecard said no"]))


# ── Promotion ───────────────────────────────────────────────────────────────

def test_promote_refuses_non_promotable(domain_repo: Path, registry: Path):
    c = _by_name(up.discover_domain_skills(domain_repo, registry=registry))[
        "brainstorming"]
    with pytest.raises(up.PromotionError, match="not promotable"):
        up.promote_to_registry(c, DOMAIN, registry, domain_repo=domain_repo)


def test_dry_run_writes_nothing(domain_repo: Path, registry: Path):
    c = _by_name(up.discover_domain_skills(domain_repo, registry=registry))[
        "widget-triage"]
    before = json.loads((registry / "registry.json").read_text())

    result = up.promote_to_registry(c, DOMAIN, registry, domain_repo=domain_repo,
                                    dry_run=True)

    assert not (registry / "skills" / "widget-triage").exists()
    assert json.loads((registry / "registry.json").read_text()) == before
    assert result.committed is False
    assert result.files > 0


def test_promote_copies_skill_and_upserts_registry(domain_repo: Path, registry: Path):
    (domain_repo / ".skills" / "widget-triage" / "scripts").mkdir()
    (domain_repo / ".skills" / "widget-triage" / "scripts" / "run.py").write_text(
        "print('hi')\n", encoding="utf-8")
    c = _by_name(up.discover_domain_skills(domain_repo, registry=registry))[
        "widget-triage"]

    result = up.promote_to_registry(c, DOMAIN, registry, domain_repo=domain_repo)

    dest = registry / "skills" / "widget-triage"
    assert (dest / "SKILL.md").is_file()
    assert (dest / "scripts" / "run.py").is_file(), "companion files must come along"

    entry = next(s for s in json.loads((registry / "registry.json").read_text())["skills"]
                 if s["name"] == "widget-triage")
    assert entry["description"] == "Does a useful thing"
    assert "alpha" in entry["tags"]
    assert f"domain:{DOMAIN}" in entry["tags"], "provenance must be recorded"
    assert result.kind == up.NEW


def test_promote_preserves_registry_curation_on_update(domain_repo: Path, registry: Path):
    """An update must not clobber registry-side curation (auto_detect, tags)."""
    _write_skill(domain_repo / ".skills", "java-spring-boot",
                 body="Improved.", description="Spring Boot, improved")
    c = _by_name(up.discover_domain_skills(domain_repo, registry=registry))[
        "java-spring-boot"]

    up.promote_to_registry(c, DOMAIN, registry, domain_repo=domain_repo)

    entry = next(s for s in json.loads((registry / "registry.json").read_text())["skills"]
                 if s["name"] == "java-spring-boot")
    assert entry["auto_detect"] == {"files": ["pom.xml"]}, "curation must survive"
    assert "java" in entry["tags"]
    assert entry["description"] == "Spring Boot, improved"


def test_promote_commits_on_a_branch_without_pushing(domain_repo: Path, registry: Path):
    c = _by_name(up.discover_domain_skills(domain_repo, registry=registry))[
        "widget-triage"]

    result = up.promote_to_registry(c, DOMAIN, registry, domain_repo=domain_repo)

    assert result.committed is True
    assert result.branch == f"skill-promote/{DOMAIN}/widget-triage"
    assert result.pushed is False, "publishing must stay an explicit human step"
    assert "git -C" in result.push_hint and "push" in result.push_hint

    branch = subprocess.run(["git", "-C", str(registry), "rev-parse",
                             "--abbrev-ref", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    assert branch == result.branch

    log = subprocess.run(["git", "-C", str(registry), "log", "-1", "--pretty=%B"],
                         capture_output=True, text=True).stdout
    assert "widget-triage" in log and DOMAIN in log


def test_promote_no_commit_leaves_files_only(domain_repo: Path, registry: Path):
    c = _by_name(up.discover_domain_skills(domain_repo, registry=registry))[
        "widget-triage"]

    result = up.promote_to_registry(c, DOMAIN, registry, domain_repo=domain_repo,
                                    commit=False)

    assert (registry / "skills" / "widget-triage" / "SKILL.md").is_file()
    assert result.committed is False
    assert result.branch == ""


def test_promote_handles_non_git_registry(domain_repo: Path, tmp_path: Path):
    plain = tmp_path / "plain-registry"
    (plain / "skills").mkdir(parents=True)
    (plain / "registry.json").write_text(json.dumps({"skills": []}))
    c = _by_name(up.discover_domain_skills(domain_repo, registry=plain))["widget-triage"]

    result = up.promote_to_registry(c, DOMAIN, plain, domain_repo=domain_repo)

    assert (plain / "skills" / "widget-triage" / "SKILL.md").is_file()
    assert result.committed is False
    assert "not a git repository" in result.push_hint


def test_promotion_is_logged_to_the_evolution_log(domain_repo: Path, registry: Path):
    c = _by_name(up.discover_domain_skills(domain_repo, registry=registry))[
        "widget-triage"]

    up.promote_to_registry(c, DOMAIN, registry, domain_repo=domain_repo)

    log = json.loads(
        (domain_repo / ".domain" / "skills-evolution.json").read_text())
    events = [e["event"] for e in log["widget-triage"]]
    assert "contributed" in events


def test_branch_name_is_hierarchical_and_sanitized():
    assert up.branch_name("cwow-apoc", "my-skill") == "skill-promote/cwow-apoc/my-skill"
    # No empty components or traversal, which git would reject.
    assert up.branch_name("..", "a b") == "skill-promote/a-b"


def test_promote_rejects_unsafe_name(domain_repo: Path, registry: Path):
    c = _by_name(up.discover_domain_skills(domain_repo, registry=registry))[
        "widget-triage"]
    c.name = "../escape"
    with pytest.raises(up.PromotionError, match="Unsafe skill name"):
        up.promote_to_registry(c, DOMAIN, registry, domain_repo=domain_repo)


def test_discover_for_domain_missing_repo_raises():
    with pytest.raises(FileNotFoundError, match="No context-meta repo"):
        up.discover_for_domain("definitely-not-a-real-domain-xyz")


def test_candidates_serialize(domain_repo: Path, registry: Path):
    payload = [c.to_dict() for c in
               up.discover_domain_skills(domain_repo, registry=registry)]
    assert json.loads(json.dumps(payload))
    assert any(c["promotable"] for c in payload)
