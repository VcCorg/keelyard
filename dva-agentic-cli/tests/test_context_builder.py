"""Tests for kg/context_builder.py — KG context generation from onboard analysis."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dva_agentic_cli.analyzer.detector import ProjectAnalysis
from dva_agentic_cli.kg.context_builder import (
    build_kg_context_document,
    build_skill_kg_instructions,
    ingest_context_to_lightrag,
    patch_skill_md_with_kg_instructions,
    register_kg_data_source,
    run_kg_context_pipeline,
    save_kg_context,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_analysis() -> ProjectAnalysis:
    """Create a realistic ProjectAnalysis for testing."""
    analysis = ProjectAnalysis()
    analysis.languages = ["java", "python"]
    analysis.frameworks = ["spring-boot", "fastapi"]
    analysis.build_tools = ["gradle", "pip"]
    analysis.test_frameworks = ["junit", "pytest"]
    analysis.databases = ["spanner", "postgres"]
    analysis.api_types = ["REST", "gRPC"]
    analysis.ci_cd = ["jenkins", "github-actions"]
    analysis.has_docker = True
    analysis.dependencies = ["spring-boot-starter", "fastapi", "uvicorn", "pydantic"]
    analysis.raw_dependencies = {
        "spring-boot-starter": "3.2.0",
        "fastapi": "0.104.1",
        "uvicorn": "0.24.0",
        "pydantic": "2.5.0",
    }
    analysis.module_structure = ["src/main", "src/api", "src/service", "src/model", "tests"]
    analysis.entry_points = ["src/main/Application.java", "src/main.py"]
    analysis.source_patterns = ["MVC pattern", "Repository pattern"]
    analysis.project_files = {
        "build.gradle": True,
        "pyproject.toml": True,
        "Dockerfile": True,
        "Jenkinsfile": True,
        "README.md": True,
    }
    return analysis


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create a minimal project directory with skills dir."""
    project = tmp_path / "my-test-project"
    project.mkdir()
    skills_dir = project / ".skills" / "project-context"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text(
        "---\nname: project-context\n---\n\n# Project: my-test-project\n\n## Tech Stack\n"
    )
    return project


@pytest.fixture
def empty_project_dir(tmp_path: Path) -> Path:
    """Create a project directory without .skills."""
    project = tmp_path / "empty-project"
    project.mkdir()
    return project


# ---------------------------------------------------------------------------
# build_kg_context_document
# ---------------------------------------------------------------------------

class TestBuildKGContextDocument:
    """Tests for the context document generator."""

    def test_contains_project_name(self, project_dir, sample_analysis):
        doc = build_kg_context_document(project_dir, sample_analysis, ["project-context"])
        assert "my-test-project" in doc

    def test_contains_tech_stack_table(self, project_dir, sample_analysis):
        doc = build_kg_context_document(project_dir, sample_analysis, ["project-context"])
        assert "| **Languages** | java, python |" in doc
        assert "| **Frameworks** | spring-boot, fastapi |" in doc
        assert "| **Docker** | Yes |" in doc

    def test_contains_module_structure(self, project_dir, sample_analysis):
        doc = build_kg_context_document(project_dir, sample_analysis, ["project-context"])
        assert "## Architecture — Module Structure" in doc
        assert "- src/main" in doc
        assert "- src/api" in doc

    def test_contains_entry_points(self, project_dir, sample_analysis):
        doc = build_kg_context_document(project_dir, sample_analysis, ["project-context"])
        assert "## Entry Points" in doc
        assert "- src/main/Application.java" in doc

    def test_contains_dependencies_with_versions(self, project_dir, sample_analysis):
        doc = build_kg_context_document(project_dir, sample_analysis, ["project-context"])
        assert "## Dependencies (4 total)" in doc
        assert "`fastapi` (0.104.1)" in doc

    def test_contains_source_patterns(self, project_dir, sample_analysis):
        doc = build_kg_context_document(project_dir, sample_analysis, ["project-context"])
        assert "## Source Code Patterns" in doc
        assert "- MVC pattern" in doc

    def test_contains_integration_points(self, project_dir, sample_analysis):
        doc = build_kg_context_document(project_dir, sample_analysis, ["project-context"])
        assert "## Integration Points" in doc
        assert "- Database: spanner" in doc
        assert "- API: REST" in doc
        assert "- CI/CD: jenkins" in doc

    def test_contains_installed_skills(self, project_dir, sample_analysis):
        doc = build_kg_context_document(
            project_dir, sample_analysis, ["project-context", "java-spring-boot"]
        )
        assert "## Installed Skills (2)" in doc
        assert "- java-spring-boot" in doc

    def test_contains_suggested_skills(self, project_dir, sample_analysis):
        doc = build_kg_context_document(
            project_dir, sample_analysis, ["project-context"], suggested_skills=["docker"]
        )
        assert "## Suggested Skills (1)" in doc
        assert "- docker" in doc

    def test_contains_key_project_files(self, project_dir, sample_analysis):
        doc = build_kg_context_document(project_dir, sample_analysis, ["project-context"])
        assert "## Key Project Files" in doc
        assert "- Dockerfile" in doc
        assert "- build.gradle" in doc

    def test_minimal_analysis(self, project_dir):
        """Empty analysis should still produce valid markdown."""
        analysis = ProjectAnalysis()
        doc = build_kg_context_document(project_dir, analysis, [])
        assert "# Project Context:" in doc
        assert "Unknown" in doc  # languages default
        assert "_None detected_" in doc

    def test_truncation_for_large_lists(self, project_dir):
        """Lists longer than the limit should be truncated."""
        analysis = ProjectAnalysis()
        analysis.languages = ["lang"]
        analysis.dependencies = [f"dep-{i}" for i in range(60)]
        analysis.raw_dependencies = {}
        doc = build_kg_context_document(project_dir, analysis, [])
        assert "... and 20 more" in doc


# ---------------------------------------------------------------------------
# build_skill_kg_instructions
# ---------------------------------------------------------------------------

class TestBuildSkillKGInstructions:
    def test_contains_tool_calls(self):
        text = build_skill_kg_instructions("my-project")
        assert 'get_project_context(project="my-project")' in text
        assert "search_business_context" in text

    def test_contains_context_first_header(self):
        text = build_skill_kg_instructions("x")
        assert "## Context-First Workflow (Knowledge Graph)" in text


# ---------------------------------------------------------------------------
# save_kg_context
# ---------------------------------------------------------------------------

class TestSaveKGContext:
    def test_creates_file(self, project_dir, sample_analysis):
        result = save_kg_context(project_dir, sample_analysis, ["project-context"])
        assert result.exists()
        assert result.name == "kg-context.md"
        content = result.read_text()
        assert "my-test-project" in content

    def test_creates_skills_dir_if_missing(self, empty_project_dir, sample_analysis):
        result = save_kg_context(empty_project_dir, sample_analysis, [])
        assert result.exists()
        assert (empty_project_dir / ".skills" / "project-context").is_dir()

    def test_overwrites_existing(self, project_dir, sample_analysis):
        first = save_kg_context(project_dir, sample_analysis, ["a"])
        content1 = first.read_text()
        second = save_kg_context(project_dir, sample_analysis, ["a", "b"])
        content2 = second.read_text()
        assert content1 != content2
        assert "## Installed Skills (2)" in content2


# ---------------------------------------------------------------------------
# patch_skill_md_with_kg_instructions
# ---------------------------------------------------------------------------

class TestPatchSkillMD:
    def test_appends_instructions(self, project_dir):
        result = patch_skill_md_with_kg_instructions(project_dir)
        assert result is True
        content = (project_dir / ".skills" / "project-context" / "SKILL.md").read_text()
        assert "## Context-First Workflow (Knowledge Graph)" in content
        assert "my-test-project" in content

    def test_idempotent(self, project_dir):
        patch_skill_md_with_kg_instructions(project_dir)
        result = patch_skill_md_with_kg_instructions(project_dir)
        assert result is False  # already patched

    def test_returns_false_if_no_skill_md(self, empty_project_dir):
        result = patch_skill_md_with_kg_instructions(empty_project_dir)
        assert result is False


# ---------------------------------------------------------------------------
# register_kg_data_source
# ---------------------------------------------------------------------------

class TestRegisterKGDataSource:
    def test_registers_source(self, project_dir, sample_analysis, tmp_path):
        with patch("dva_agentic_cli.kg.context_builder.Path") as mock_path_cls:
            # Redirect home() to tmp
            config_dir = tmp_path / ".dva-agentic"
            config_file = config_dir / "config.json"
            config_dir.mkdir(parents=True)

            # We need a more surgical patch — just mock Path.home()
            pass

        # Direct test: use real filesystem with mocked home
        fake_home = tmp_path / "fakehome"
        fake_home.mkdir()
        config_dir = fake_home / ".dva-agentic"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({"data": {"globals": {}, "sources": []}}))

        with patch(
            "dva_agentic_cli.kg.context_builder.Path.home", return_value=fake_home
        ):
            source = register_kg_data_source(project_dir, sample_analysis)

        assert source["name"] == "onboard-my-test-project"
        assert source["type"] == "doc"
        assert "project-context" in source["location"]
        assert "java" in source["tags"]
        assert "onboard" in source["tags"]
        assert source["project"] == "my-test-project"

        # Verify config file was updated
        saved = json.loads(config_file.read_text())
        assert len(saved["data"]["sources"]) == 1
        assert saved["data"]["sources"][0]["name"] == "onboard-my-test-project"

    def test_idempotent_overwrites(self, project_dir, sample_analysis, tmp_path):
        fake_home = tmp_path / "fakehome"
        config_dir = fake_home / ".dva-agentic"
        config_dir.mkdir(parents=True)
        (config_dir / "config.json").write_text(
            json.dumps({"data": {"globals": {}, "sources": []}})
        )

        with patch(
            "dva_agentic_cli.kg.context_builder.Path.home", return_value=fake_home
        ):
            register_kg_data_source(project_dir, sample_analysis)
            register_kg_data_source(project_dir, sample_analysis)

        saved = json.loads((config_dir / "config.json").read_text())
        # Should still be exactly 1 entry, not 2
        assert len(saved["data"]["sources"]) == 1

    def test_creates_config_from_scratch(self, project_dir, sample_analysis, tmp_path):
        fake_home = tmp_path / "fakehome"
        (fake_home / ".dva-agentic").mkdir(parents=True)

        with patch(
            "dva_agentic_cli.kg.context_builder.Path.home", return_value=fake_home
        ):
            source = register_kg_data_source(project_dir, sample_analysis)

        assert source["name"] == "onboard-my-test-project"
        config_file = fake_home / ".dva-agentic" / "config.json"
        assert config_file.exists()


# ---------------------------------------------------------------------------
# ingest_context_to_lightrag
# ---------------------------------------------------------------------------

class TestIngestContextToLightRAG:
    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ingest_context_to_lightrag(
                tmp_path / "nonexistent.md", "test-project"
            )

    def test_calls_lightrag_client(self, project_dir, sample_analysis):
        ctx = save_kg_context(project_dir, sample_analysis, [])

        mock_client = MagicMock()
        mock_client.insert.return_value = {"characters": 500, "status": "ok"}

        with patch(
            "dva_agentic_cli.kg.lightrag_client.LightRAGClient",
            return_value=mock_client,
        ):
            result = ingest_context_to_lightrag(ctx, "my-test-project")

        mock_client.insert.assert_called_once()
        call_args = mock_client.insert.call_args
        assert "my-test-project" in call_args[0][0]  # text content (1st positional)
        assert call_args[0][1]["project"] == "my-test-project"  # metadata (2nd positional)
        assert result["status"] == "ok"
        mock_client.close.assert_called_once()


# ---------------------------------------------------------------------------
# run_kg_context_pipeline
# ---------------------------------------------------------------------------

class TestRunKGContextPipeline:
    def test_full_pipeline_without_ingest(self, project_dir, sample_analysis, tmp_path):
        fake_home = tmp_path / "fakehome"
        (fake_home / ".dva-agentic").mkdir(parents=True)

        with patch(
            "dva_agentic_cli.kg.context_builder.Path.home", return_value=fake_home
        ):
            result = run_kg_context_pipeline(
                project_dir, sample_analysis, ["project-context"],
                ingest=False,
            )

        assert result["context_path"] is not None
        assert Path(result["context_path"]).exists()
        assert result["source"]["name"] == "onboard-my-test-project"
        assert result["skill_patched"] is True
        assert result["ingested"] is False
        assert result["errors"] == []

    def test_pipeline_with_ingest(self, project_dir, sample_analysis, tmp_path):
        fake_home = tmp_path / "fakehome"
        (fake_home / ".dva-agentic").mkdir(parents=True)

        mock_client = MagicMock()
        mock_client.insert.return_value = {"characters": 100}

        with patch(
            "dva_agentic_cli.kg.context_builder.Path.home", return_value=fake_home
        ), patch(
            "dva_agentic_cli.kg.lightrag_client.LightRAGClient",
            return_value=mock_client,
        ):
            result = run_kg_context_pipeline(
                project_dir, sample_analysis, ["project-context"],
                ingest=True,
            )

        assert result["ingested"] is True
        assert result["ingest_result"]["characters"] == 100

    def test_pipeline_records_lightrag_errors(self, project_dir, sample_analysis, tmp_path):
        fake_home = tmp_path / "fakehome"
        (fake_home / ".dva-agentic").mkdir(parents=True)

        with patch(
            "dva_agentic_cli.kg.context_builder.Path.home", return_value=fake_home
        ), patch(
            "dva_agentic_cli.kg.lightrag_client.LightRAGClient",
            side_effect=ConnectionError("refused"),
        ):
            result = run_kg_context_pipeline(
                project_dir, sample_analysis, ["project-context"],
                ingest=True,
            )

        assert result["ingested"] is False
        assert any("LightRAG ingestion failed" in e for e in result["errors"])
        # Context + source should still be created
        assert result["context_path"] is not None
        assert result["source"] is not None

    def test_pipeline_idempotent(self, project_dir, sample_analysis, tmp_path):
        """Running the pipeline twice should not duplicate data sources."""
        fake_home = tmp_path / "fakehome"
        (fake_home / ".dva-agentic").mkdir(parents=True)

        with patch(
            "dva_agentic_cli.kg.context_builder.Path.home", return_value=fake_home
        ):
            run_kg_context_pipeline(
                project_dir, sample_analysis, ["project-context"], ingest=False
            )
            result = run_kg_context_pipeline(
                project_dir, sample_analysis, ["project-context", "java-spring-boot"],
                ingest=False,
            )

        # SKILL.md should not be re-patched
        assert result["skill_patched"] is False
        # Config should have exactly 1 source
        config = json.loads(
            (fake_home / ".dva-agentic" / "config.json").read_text()
        )
        assert len(config["data"]["sources"]) == 1
