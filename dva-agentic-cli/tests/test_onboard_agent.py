"""Tests for the onboard agent — skill gap detection, proposal management, and registry updates."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from dva_agentic_cli.analyzer.detector import ProjectAnalysis
from dva_agentic_cli.analyzer.matcher import (
    SkillProposal,
    save_proposals,
    load_proposals,
    accept_proposal,
    remove_proposal,
    PROPOSALS_DIR,
)


# --- Fixtures ---


@pytest.fixture
def sample_analysis():
    """Create a sample ProjectAnalysis for testing."""
    a = ProjectAnalysis()
    a.languages = ["java"]
    a.frameworks = ["spring-boot"]
    a.build_tools = ["maven"]
    a.test_frameworks = ["junit"]
    a.databases = ["spanner"]
    a.api_types = ["REST"]
    a.ci_cd = ["jenkins"]
    a.has_docker = True
    a.dependencies = [
        "org.springframework.boot:spring-boot-starter-web",
        "com.google.cloud:spring-cloud-gcp-starter-data-spanner",
        "org.liquibase:liquibase-core",
        "org.liquibase.ext:liquibase-spanner",
    ]
    a.raw_dependencies = {d: "" for d in a.dependencies}
    a.source_patterns = ["@RestController", "@SpringBootApplication"]
    return a


@pytest.fixture
def sample_registry():
    """Minimal registry for testing."""
    return {
        "skills": [
            {
                "name": "java-spring-boot",
                "description": "Spring Boot development",
                "tags": ["java", "spring"],
                "auto_detect": {
                    "files": ["pom.xml"],
                    "dependencies": ["spring-boot"],
                },
            },
            {
                "name": "database-spanner",
                "description": "Cloud Spanner",
                "tags": ["database", "gcp"],
                "auto_detect": {
                    "dependencies": ["spanner"],
                },
            },
        ],
    }


@pytest.fixture
def sample_proposals():
    """Sample skill proposals."""
    return [
        SkillProposal(
            skill_name="spring-cloud-gcp",
            description="Spring Cloud GCP integration patterns",
            tags=["java", "gcp", "spring"],
            reason="Found dependency spring-cloud-gcp-starter-data-spanner",
            auto_detect={"dependencies": ["spring-cloud-gcp"]},
            content="---\nname: spring-cloud-gcp\ndescription: Spring Cloud GCP\n---\n# Spring Cloud GCP\n",
            project="my-project",
        ),
        SkillProposal(
            skill_name="liquibase-spanner",
            description="Liquibase with Cloud Spanner",
            tags=["database", "migration"],
            reason="Found dependency liquibase-spanner",
            auto_detect={"dependencies_all": ["liquibase-core", "liquibase-spanner"]},
            content="---\nname: liquibase-spanner\n---\n# Liquibase Spanner\n",
            project="my-project",
        ),
    ]


@pytest.fixture
def temp_proposals_dir(tmp_path, monkeypatch):
    """Redirect PROPOSALS_DIR to a temp directory."""
    proposals = tmp_path / "proposals"
    proposals.mkdir()
    monkeypatch.setattr("dva_agentic_cli.analyzer.matcher.PROPOSALS_DIR", proposals)
    return proposals


@pytest.fixture
def temp_registry(tmp_path, sample_registry):
    """Create a temp registry directory with registry.json and skills/."""
    reg = tmp_path / "registry"
    reg.mkdir()
    (reg / "registry.json").write_text(json.dumps(sample_registry, indent=2))
    (reg / "skills").mkdir()
    return reg


# --- SkillProposal tests ---


class TestSkillProposal:
    def test_to_dict(self, sample_proposals):
        p = sample_proposals[0]
        d = p.to_dict()
        assert d["skill_name"] == "spring-cloud-gcp"
        assert d["description"] == "Spring Cloud GCP integration patterns"
        assert "java" in d["tags"]
        assert d["auto_detect"]["dependencies"] == ["spring-cloud-gcp"]
        assert d["content"].startswith("---")

    def test_from_dict(self):
        data = {
            "skill_name": "test-skill",
            "description": "Test",
            "tags": ["test"],
            "reason": "testing",
            "auto_detect": {"files": ["test.txt"]},
            "content": "# Test",
            "project": "proj",
        }
        p = SkillProposal.from_dict(data)
        assert p.skill_name == "test-skill"
        assert p.tags == ["test"]
        assert p.auto_detect == {"files": ["test.txt"]}

    def test_roundtrip(self, sample_proposals):
        p = sample_proposals[0]
        d = p.to_dict()
        p2 = SkillProposal.from_dict(d)
        assert p2.skill_name == p.skill_name
        assert p2.description == p.description
        assert p2.tags == p.tags
        assert p2.auto_detect == p.auto_detect


# --- Proposal storage tests ---


class TestProposalStorage:
    def test_save_and_load(self, temp_proposals_dir, sample_proposals):
        save_proposals(sample_proposals, "my-project")
        loaded = load_proposals("my-project")
        assert len(loaded) == 2
        assert loaded[0].skill_name == "spring-cloud-gcp"
        assert loaded[1].skill_name == "liquibase-spanner"

    def test_load_all(self, temp_proposals_dir, sample_proposals):
        save_proposals(sample_proposals[:1], "project-a")
        save_proposals(sample_proposals[1:], "project-b")
        all_proposals = load_proposals()
        assert len(all_proposals) == 2

    def test_load_empty(self, temp_proposals_dir):
        loaded = load_proposals("nonexistent")
        assert loaded == []

    def test_load_no_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "dva_agentic_cli.analyzer.matcher.PROPOSALS_DIR",
            tmp_path / "does-not-exist",
        )
        loaded = load_proposals()
        assert loaded == []


# --- accept_proposal tests ---


class TestAcceptProposal:
    def test_accept_adds_to_registry(self, temp_registry, sample_proposals):
        p = sample_proposals[0]
        result = accept_proposal(p, temp_registry)
        assert result is True

        # Verify registry.json updated
        reg = json.loads((temp_registry / "registry.json").read_text())
        names = [s["name"] for s in reg["skills"]]
        assert "spring-cloud-gcp" in names

        # Verify SKILL.md created
        skill_md = temp_registry / "skills" / "spring-cloud-gcp" / "SKILL.md"
        assert skill_md.exists()
        assert "spring-cloud-gcp" in skill_md.read_text()

    def test_accept_duplicate_returns_false(self, temp_registry, sample_proposals):
        # java-spring-boot already exists in registry
        p = SkillProposal(
            skill_name="java-spring-boot",
            description="Duplicate",
            tags=[],
            reason="",
            auto_detect={},
            content="",
            project="test",
        )
        result = accept_proposal(p, temp_registry)
        assert result is False

    def test_accept_preserves_auto_detect(self, temp_registry, sample_proposals):
        p = sample_proposals[1]
        accept_proposal(p, temp_registry)
        reg = json.loads((temp_registry / "registry.json").read_text())
        entry = [s for s in reg["skills"] if s["name"] == "liquibase-spanner"][0]
        assert "auto_detect" in entry
        assert entry["auto_detect"]["dependencies_all"] == ["liquibase-core", "liquibase-spanner"]

    def test_accept_missing_registry(self, tmp_path, sample_proposals):
        result = accept_proposal(sample_proposals[0], tmp_path / "nonexistent")
        assert result is False


# --- remove_proposal tests ---


class TestRemoveProposal:
    def test_remove_one(self, temp_proposals_dir, sample_proposals):
        save_proposals(sample_proposals, "my-project")
        result = remove_proposal("my-project", "spring-cloud-gcp")
        assert result is True

        remaining = load_proposals("my-project")
        assert len(remaining) == 1
        assert remaining[0].skill_name == "liquibase-spanner"

    def test_remove_last_deletes_file(self, temp_proposals_dir):
        proposals = [
            SkillProposal(
                skill_name="only-one",
                description="",
                tags=[],
                reason="",
                auto_detect={},
                project="proj",
            )
        ]
        save_proposals(proposals, "proj")
        remove_proposal("proj", "only-one")
        assert not (temp_proposals_dir / "proj.json").exists()

    def test_remove_nonexistent(self, temp_proposals_dir, sample_proposals):
        save_proposals(sample_proposals, "my-project")
        result = remove_proposal("my-project", "no-such-skill")
        assert result is False

    def test_remove_no_file(self, temp_proposals_dir):
        result = remove_proposal("no-project", "any-skill")
        assert result is False


# --- Onboard agent tests (mocked Vertex AI) ---


class TestOnboardAgent:
    @patch("dva_agentic_cli.agents.onboard.gap_detector.init_model")
    def test_detect_skill_gaps(self, mock_init, sample_analysis, sample_registry):
        from dva_agentic_cli.agents.onboard.gap_detector import detect_skill_gaps

        mock_model = MagicMock()
        mock_model.generate_content.return_value = MagicMock(
            text=json.dumps([
                {
                    "skill_name": "spring-cloud-gcp",
                    "description": "Spring Cloud GCP patterns",
                    "tags": ["java", "gcp"],
                    "reason": "Uses spring-cloud-gcp-starter",
                    "auto_detect": {"dependencies": ["spring-cloud-gcp"]},
                }
            ])
        )
        mock_init.return_value = mock_model

        gaps = detect_skill_gaps(
            sample_analysis,
            ["java-spring-boot", "database-spanner"],
            sample_registry,
        )

        assert len(gaps) == 1
        assert gaps[0]["skill_name"] == "spring-cloud-gcp"
        assert "gcp" in gaps[0]["tags"]
        mock_model.generate_content.assert_called_once()

    @patch("dva_agentic_cli.agents.onboard.gap_detector.init_model")
    def test_detect_skill_gaps_empty(self, mock_init, sample_analysis, sample_registry):
        from dva_agentic_cli.agents.onboard.gap_detector import detect_skill_gaps

        mock_model = MagicMock()
        mock_model.generate_content.return_value = MagicMock(text="[]")
        mock_init.return_value = mock_model

        gaps = detect_skill_gaps(sample_analysis, [], sample_registry)
        assert gaps == []

    @patch("dva_agentic_cli.agents.onboard.gap_detector.init_model")
    def test_detect_skill_gaps_malformed_response(self, mock_init, sample_analysis, sample_registry):
        from dva_agentic_cli.agents.onboard.gap_detector import detect_skill_gaps

        mock_model = MagicMock()
        mock_model.generate_content.return_value = MagicMock(text="not json at all")
        mock_init.return_value = mock_model

        gaps = detect_skill_gaps(sample_analysis, [], sample_registry)
        assert gaps == []

    @patch("dva_agentic_cli.agents.onboard.skill_generator.init_model")
    def test_generate_skill_content(self, mock_init):
        from dva_agentic_cli.agents.onboard.skill_generator import generate_skill_content

        expected_content = "---\nname: test-skill\n---\n# Test Skill\n\n## Guidelines\n- Do stuff"
        mock_model = MagicMock()
        mock_model.generate_content.return_value = MagicMock(text=expected_content)
        mock_init.return_value = mock_model

        content = generate_skill_content("test-skill", "Test", ["test"], "testing")
        assert "test-skill" in content
        mock_model.generate_content.assert_called_once()

    @patch("dva_agentic_cli.agents.onboard.skill_generator.init_model")
    def test_generate_skill_content_fallback(self, mock_init):
        from dva_agentic_cli.agents.onboard.skill_generator import generate_skill_content

        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API error")
        mock_init.return_value = mock_model

        content = generate_skill_content("test-skill", "Test desc", ["test"], "testing")
        assert "test-skill" in content
        assert "TODO" in content

    @patch("dva_agentic_cli.agents.onboard.models.init_model")
    def test_run_onboard_agent(self, mock_init, sample_analysis, sample_registry, tmp_path):
        from dva_agentic_cli.agents.onboard.pipeline import run_onboard_pipeline

        gap_response = json.dumps([
            {
                "skill_name": "new-skill",
                "description": "A new skill",
                "tags": ["new"],
                "reason": "Detected pattern",
                "auto_detect": {},
            }
        ])
        content_response = "---\nname: new-skill\n---\n# New Skill"

        mock_model = MagicMock()
        mock_model.generate_content.side_effect = [
            MagicMock(text=gap_response),
            MagicMock(text=content_response),
        ]
        mock_init.return_value = mock_model

        result = run_onboard_pipeline(
            analysis=sample_analysis,
            installed_skills=["java-spring-boot"],
            registry=sample_registry,
            registry_path=tmp_path,
            project_path=tmp_path,
            enrich=False,
            model=mock_model,
        )

        assert len(result["proposals"]) == 1
        assert result["proposals"][0]["skill_name"] == "new-skill"
        assert result["proposals"][0]["content"] == content_response
        assert result["errors"] == []


# --- JSON response parsing tests ---


class TestParseJsonResponse:
    def test_plain_json(self):
        from dva_agentic_cli.agents.onboard.models import parse_json_response

        result = parse_json_response('[{"a": 1}]')
        assert result == [{"a": 1}]

    def test_fenced_json(self):
        from dva_agentic_cli.agents.onboard.models import parse_json_response

        text = '```json\n[{"a": 1}]\n```'
        result = parse_json_response(text)
        assert result == [{"a": 1}]

    def test_fenced_no_lang(self):
        from dva_agentic_cli.agents.onboard.models import parse_json_response

        text = '```\n[{"a": 1}]\n```'
        result = parse_json_response(text)
        assert result == [{"a": 1}]
