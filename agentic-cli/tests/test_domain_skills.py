"""Tests for kg/domain_skills.py — skill discovery, injection, manifest, validation."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from agentic_cli.kg.domain_skills import (
    discover_skills,
    generate_skills_manifest,
    load_skills_manifest,
    update_skill_status,
    log_skill_event,
    fork_skill,
    load_domain_skills,
    install_domain_skill,
    bootstrap_domain_skills,
    _extract_skill_description,
    _generate_skills_manifest_md,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def skills_source(tmp_path: Path) -> Path:
    """Create a minimal superpowers-like skills directory."""
    skills = tmp_path / "skills"
    skills.mkdir()

    # Skill 1: requesting-code-review
    s1 = skills / "requesting-code-review"
    s1.mkdir()
    (s1 / "SKILL.md").write_text(
        "---\nname: requesting-code-review\n---\n\n"
        "# Requesting Code Review\n\n"
        "How to request thorough code reviews from AI assistants."
    )

    # Skill 2: test-driven-development
    s2 = skills / "test-driven-development"
    s2.mkdir()
    (s2 / "SKILL.md").write_text(
        "---\nname: test-driven-development\n---\n\n"
        "# Test-Driven Development\n\n"
        "Write tests before implementation code."
    )
    (s2 / "examples.md").write_text("# Examples\n\nSome examples here.")

    # Not a skill (no SKILL.md)
    s3 = skills / "random-dir"
    s3.mkdir()
    (s3 / "README.md").write_text("Not a skill")

    return tmp_path


@pytest.fixture
def domain_context_dir(tmp_path: Path) -> Path:
    """Create a minimal domain-context repo structure."""
    d = tmp_path / "cwow-facility-domain-context"
    d.mkdir()
    (d / ".domain").mkdir()
    (d / ".skills").mkdir()
    return d


@pytest.fixture
def sample_skills() -> list[dict]:
    return [
        {
            "name": "requesting-code-review",
            "path": "/fake/skills/requesting-code-review",
            "description": "How to request thorough code reviews.",
            "files": ["SKILL.md"],
            "has_skill_md": True,
        },
        {
            "name": "test-driven-development",
            "path": "/fake/skills/test-driven-development",
            "description": "Write tests before implementation.",
            "files": ["SKILL.md", "examples.md"],
            "has_skill_md": True,
        },
    ]


# ---------------------------------------------------------------------------
# Tests: Skill discovery
# ---------------------------------------------------------------------------

class TestDiscoverSkills:
    def test_discover_finds_skills_with_skill_md(self, skills_source: Path):
        skills = discover_skills(skills_source)
        names = [s["name"] for s in skills]
        assert "requesting-code-review" in names
        assert "test-driven-development" in names

    def test_discover_ignores_dirs_without_skill_md(self, skills_source: Path):
        skills = discover_skills(skills_source)
        names = [s["name"] for s in skills]
        assert "random-dir" not in names

    def test_discover_returns_empty_for_missing_dir(self, tmp_path: Path):
        skills = discover_skills(tmp_path / "nonexistent")
        assert skills == []

    def test_discover_includes_files_list(self, skills_source: Path):
        skills = discover_skills(skills_source)
        tdd = next(s for s in skills if s["name"] == "test-driven-development")
        assert "SKILL.md" in tdd["files"]
        assert "examples.md" in tdd["files"]

    def test_discover_extracts_description(self, skills_source: Path):
        skills = discover_skills(skills_source)
        rcr = next(s for s in skills if s["name"] == "requesting-code-review")
        assert "code review" in rcr["description"].lower()


class TestExtractSkillDescription:
    def test_extracts_from_title_paragraph(self, tmp_path: Path):
        md = tmp_path / "SKILL.md"
        md.write_text("# My Skill\n\nThis is the description of the skill.")
        desc = _extract_skill_description(md)
        assert "description of the skill" in desc

    def test_handles_frontmatter(self, tmp_path: Path):
        md = tmp_path / "SKILL.md"
        md.write_text("---\nname: test\n---\n\n# Test Skill\n\nTest description here.")
        desc = _extract_skill_description(md)
        assert "test description" in desc.lower()

    def test_returns_empty_on_error(self, tmp_path: Path):
        md = tmp_path / "nonexistent.md"
        desc = _extract_skill_description(md)
        assert desc == ""


# ---------------------------------------------------------------------------
# Tests: Skills manifest
# ---------------------------------------------------------------------------

class TestSkillsManifest:
    def test_generate_creates_manifest_json(self, domain_context_dir: Path, sample_skills: list):
        path = generate_skills_manifest(
            domain_context_dir, "cwow-facility", sample_skills,
        )
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["domain"] == "cwow-facility"
        assert "requesting-code-review" in data["skills"]
        assert "test-driven-development" in data["skills"]
        assert data["skills"]["requesting-code-review"]["status"] == "injected"
        assert data["skills"]["requesting-code-review"]["validated"] is False

    def test_load_manifest(self, domain_context_dir: Path, sample_skills: list):
        generate_skills_manifest(domain_context_dir, "cwow-facility", sample_skills)
        loaded = load_skills_manifest(domain_context_dir)
        assert loaded["domain"] == "cwow-facility"
        assert len(loaded["skills"]) == 2

    def test_load_manifest_returns_empty_when_missing(self, tmp_path: Path):
        loaded = load_skills_manifest(tmp_path)
        assert loaded == {}

    def test_update_skill_status(self, domain_context_dir: Path, sample_skills: list):
        generate_skills_manifest(domain_context_dir, "cwow-facility", sample_skills)

        result = update_skill_status(
            domain_context_dir, "requesting-code-review",
            status="validated", validated=True, notes="Works well on PR review tasks",
        )
        assert result is True

        manifest = load_skills_manifest(domain_context_dir)
        skill = manifest["skills"]["requesting-code-review"]
        assert skill["status"] == "validated"
        assert skill["validated"] is True
        assert "Works well" in skill["notes"]
        assert skill["validation_date"] is not None

    def test_update_skill_status_not_found(self, domain_context_dir: Path, sample_skills: list):
        generate_skills_manifest(domain_context_dir, "cwow-facility", sample_skills)
        result = update_skill_status(domain_context_dir, "nonexistent", "validated")
        assert result is False


# ---------------------------------------------------------------------------
# Tests: Evolution log
# ---------------------------------------------------------------------------

class TestSkillEvolutionLog:
    def test_log_creates_file(self, domain_context_dir: Path):
        log_skill_event(domain_context_dir, "test-skill", "injected", {"source": "superpowers"})
        log_path = domain_context_dir / ".domain" / "skills-evolution.json"
        assert log_path.exists()
        data = json.loads(log_path.read_text())
        assert "test-skill" in data
        assert data["test-skill"][0]["event"] == "injected"

    def test_log_appends_events(self, domain_context_dir: Path):
        log_skill_event(domain_context_dir, "test-skill", "injected")
        log_skill_event(domain_context_dir, "test-skill", "validated", {"feedback": "works"})
        data = json.loads((domain_context_dir / ".domain" / "skills-evolution.json").read_text())
        assert len(data["test-skill"]) == 2
        assert data["test-skill"][1]["event"] == "validated"


# ---------------------------------------------------------------------------
# Tests: Skill forking
# ---------------------------------------------------------------------------

class TestForkSkill:
    def test_fork_copies_skill(self, domain_context_dir: Path, skills_source: Path):
        # Inject a skill first
        import shutil
        src = skills_source / "skills" / "requesting-code-review"
        dest = domain_context_dir / ".skills" / "requesting-code-review"
        shutil.copytree(src, dest)

        # Create manifest
        generate_skills_manifest(
            domain_context_dir, "cwow-facility",
            [{"name": "requesting-code-review", "description": "test", "files": ["SKILL.md"]}],
        )

        result = fork_skill(
            domain_context_dir, "requesting-code-review", "cwow-facility",
            reason="Add HIPAA review checks",
        )
        assert result is not None
        assert result.name == "requesting-code-review-cwow-facility"
        assert (result / "SKILL.md").exists()
        assert (result / "CUSTOMIZATION_NOTES.md").exists()

        # Check manifest updated
        manifest = load_skills_manifest(domain_context_dir)
        forked_name = "requesting-code-review-cwow-facility"
        assert forked_name in manifest["skills"]
        assert manifest["skills"][forked_name]["status"] == "forked"
        assert manifest["skills"][forked_name]["customized"] is True

    def test_fork_returns_none_for_missing_skill(self, domain_context_dir: Path):
        result = fork_skill(domain_context_dir, "nonexistent", "cwow-facility")
        assert result is None


# ---------------------------------------------------------------------------
# Tests: Load domain skills
# ---------------------------------------------------------------------------

class TestLoadDomainSkills:
    def test_load_returns_skills_with_paths(self, domain_context_dir: Path, skills_source: Path):
        import shutil
        # Copy skills
        for name in ["requesting-code-review", "test-driven-development"]:
            src = skills_source / "skills" / name
            dest = domain_context_dir / ".skills" / name
            shutil.copytree(src, dest)

        # Create manifest
        generate_skills_manifest(
            domain_context_dir, "cwow-facility",
            [
                {"name": "requesting-code-review", "description": "test", "files": ["SKILL.md"]},
                {"name": "test-driven-development", "description": "test", "files": ["SKILL.md"]},
            ],
        )

        loaded = load_domain_skills(domain_context_dir)
        assert "requesting-code-review" in loaded
        assert "test-driven-development" in loaded
        assert loaded["requesting-code-review"]["path"].exists()

    def test_load_returns_empty_without_manifest(self, tmp_path: Path):
        assert load_domain_skills(tmp_path) == {}


# ---------------------------------------------------------------------------
# Tests: Install domain skill
# ---------------------------------------------------------------------------

class TestInstallDomainSkill:
    def test_install_copies_to_target(self, skills_source: Path, tmp_path: Path):
        target = tmp_path / "my-project"
        target.mkdir()
        skill_path = skills_source / "skills" / "requesting-code-review"

        result = install_domain_skill("requesting-code-review", skill_path, target)
        assert result is True
        assert (target / ".skills" / "requesting-code-review" / "SKILL.md").exists()

    def test_install_overwrites_existing(self, skills_source: Path, tmp_path: Path):
        target = tmp_path / "my-project"
        target.mkdir()
        skill_path = skills_source / "skills" / "requesting-code-review"

        install_domain_skill("requesting-code-review", skill_path, target)
        install_domain_skill("requesting-code-review", skill_path, target)
        assert (target / ".skills" / "requesting-code-review" / "SKILL.md").exists()


# ---------------------------------------------------------------------------
# Tests: Bootstrap domain skills (integration)
# ---------------------------------------------------------------------------

class TestBootstrapDomainSkills:
    @patch("agentic_cli.kg.domain_skills.clone_superpowers")
    def test_bootstrap_with_copy(self, mock_clone, skills_source: Path, domain_context_dir: Path):
        mock_clone.return_value = skills_source

        result = bootstrap_domain_skills(
            domain_context_dir, "cwow-facility",
            use_submodule=False,
        )

        assert result["skill_count"] >= 2
        assert "requesting-code-review" in result["injected_skills"]
        assert result["manifest_path"].exists()
        assert result["manifest_md_path"].exists()

        # Check manifest content
        manifest = load_skills_manifest(domain_context_dir)
        assert "requesting-code-review" in manifest["skills"]

    @patch("agentic_cli.kg.domain_skills.clone_superpowers")
    def test_bootstrap_selective_skills(self, mock_clone, skills_source: Path, domain_context_dir: Path):
        mock_clone.return_value = skills_source

        result = bootstrap_domain_skills(
            domain_context_dir, "cwow-facility",
            use_submodule=False,
            skills_to_inject=["requesting-code-review"],
        )

        assert result["skill_count"] == 1
        assert "requesting-code-review" in result["injected_skills"]
        assert "test-driven-development" not in result["injected_skills"]


# ---------------------------------------------------------------------------
# Tests: Manifest markdown generation
# ---------------------------------------------------------------------------

class TestGenerateSkillsManifestMd:
    def test_generates_markdown_table(self, sample_skills: list):
        md = _generate_skills_manifest_md("cwow-facility", sample_skills)
        assert "cwow-facility" in md
        assert "requesting-code-review" in md
        assert "test-driven-development" in md
        assert "| Skill |" in md
