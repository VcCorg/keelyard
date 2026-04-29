"""Tests for Git-based skill registry."""

import json
import tempfile
from pathlib import Path

import pytest

from agentic_cli.evaluation.skill_registry import (
    GitSkillRegistry,
    SkillMetadata,
    SkillVersion,
    RegistryIndex,
)


@pytest.fixture
def temp_registry_dir():
    """Create temporary registry directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_skill_dir(temp_registry_dir):
    """Create a sample skill directory."""
    skill_dir = temp_registry_dir / "sample-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Sample Skill\n\nTest skill content")
    (skill_dir / "scripts").mkdir()
    (skill_dir / "reference").mkdir()
    return skill_dir


def test_skill_version():
    """Test SkillVersion creation."""
    version = SkillVersion(
        version="1.0",
        quality_score=92.0,
        effectiveness=9.2,
    )

    assert version.version == "1.0"
    assert version.quality_score == 92.0
    assert version.effectiveness == 9.2


def test_skill_metadata():
    """Test SkillMetadata creation and serialization."""
    metadata = SkillMetadata(
        id="backend-dev-skill",
        name="Backend Dev Skill",
        description="Developer context for backend",
        domain="backend",
        role="dev",
        tags=["backend", "dev"],
        latest_version="1.0",
    )

    # Test to_dict
    data = metadata.to_dict()
    assert data["id"] == "backend-dev-skill"
    assert data["name"] == "Backend Dev Skill"
    assert "backend" in data["tags"]

    # Test from_dict
    restored = SkillMetadata.from_dict(data)
    assert restored.id == metadata.id
    assert restored.domain == metadata.domain


def test_registry_index():
    """Test RegistryIndex creation and serialization."""
    metadata = SkillMetadata(
        id="skill1",
        name="Skill 1",
        description="Test",
        domain="test",
        role="tester",
        latest_version="1.0",
    )

    index = RegistryIndex(repository="https://github.com/test/skills.git")
    index.skills["skill1"] = metadata

    # Test to_dict
    data = index.to_dict()
    assert "skill1" in data["skills"]

    # Test from_dict
    restored = RegistryIndex.from_dict(data)
    assert "skill1" in restored.skills
    assert restored.repository == index.repository


def test_git_skill_registry_init(temp_registry_dir):
    """Test GitSkillRegistry initialization."""
    registry = GitSkillRegistry(
        "https://github.com/test/skills.git",
        temp_registry_dir,
    )

    assert registry.repo_url == "https://github.com/test/skills.git"
    assert registry.repo_name == "skills"
    assert registry.local_path == temp_registry_dir


def test_git_skill_registry_load_empty_index(temp_registry_dir):
    """Test loading empty index."""
    registry = GitSkillRegistry(
        "https://github.com/test/skills.git",
        temp_registry_dir,
    )

    index = registry.load_index()
    assert index.repository == "https://github.com/test/skills.git"
    assert len(index.skills) == 0


def test_git_skill_registry_publish(temp_registry_dir, sample_skill_dir):
    """Test publishing a skill."""
    registry = GitSkillRegistry(
        "https://github.com/test/skills.git",
        temp_registry_dir,
    )

    metadata = SkillMetadata(
        id="sample-skill",
        name="Sample Skill",
        description="A sample skill",
        domain="test",
        role="developer",
        latest_version="1.0",
    )

    # Publish (without git push)
    skill_id = registry.publish_skill(
        sample_skill_dir,
        metadata,
        quality_score=90.0,
        effectiveness=8.5,
    )

    assert skill_id == "sample-skill"

    # Verify files were copied
    skill_path = temp_registry_dir / "test" / "sample-skill" / "1.0"
    assert skill_path.exists()
    assert (skill_path / "SKILL.md").exists()
    assert (skill_path / "evaluation.json").exists()

    # Verify index was updated
    index = registry.load_index()
    assert "sample-skill" in index.skills
    skill = index.skills["sample-skill"]
    assert skill.latest_version == "1.0"
    assert skill.versions["1.0"].quality_score == 90.0


def test_git_skill_registry_search(temp_registry_dir, sample_skill_dir):
    """Test searching skills."""
    registry = GitSkillRegistry(
        "https://github.com/test/skills.git",
        temp_registry_dir,
    )

    # Publish multiple skills
    for i, (domain, effectiveness) in enumerate(
        [("backend", 9.0), ("frontend", 7.5), ("backend", 8.5)]
    ):
        metadata = SkillMetadata(
            id=f"skill-{i}",
            name=f"Skill {i}",
            description=f"Skill {i}",
            domain=domain,
            role="dev",
            latest_version="1.0",
        )
        registry.publish_skill(
            sample_skill_dir,
            metadata,
            quality_score=85.0,
            effectiveness=effectiveness,
        )

    # Test search by domain
    results = registry.search(domain="backend")
    assert len(results) == 2

    # Test search by effectiveness
    results = registry.search(min_effectiveness=8.0)
    assert len(results) == 2

    # Test search with multiple filters
    results = registry.search(domain="backend", min_effectiveness=9.0)
    assert len(results) == 1


def test_git_skill_registry_get_skill(temp_registry_dir, sample_skill_dir):
    """Test getting skill from registry."""
    registry = GitSkillRegistry(
        "https://github.com/test/skills.git",
        temp_registry_dir,
    )

    metadata = SkillMetadata(
        id="test-skill",
        name="Test Skill",
        description="Test",
        domain="test",
        role="dev",
        latest_version="1.0",
    )

    registry.publish_skill(
        sample_skill_dir,
        metadata,
        quality_score=85.0,
        effectiveness=8.0,
    )

    # Get skill
    skill_path = registry.get_skill("test-skill")
    assert skill_path is not None
    assert skill_path.exists()

    # Get non-existent skill
    skill_path = registry.get_skill("non-existent")
    assert skill_path is None


def test_git_skill_registry_install(temp_registry_dir, sample_skill_dir):
    """Test installing skill from registry."""
    registry = GitSkillRegistry(
        "https://github.com/test/skills.git",
        temp_registry_dir,
    )

    metadata = SkillMetadata(
        id="install-test",
        name="Install Test",
        description="Test",
        domain="test",
        role="dev",
        latest_version="1.0",
    )

    registry.publish_skill(
        sample_skill_dir,
        metadata,
        quality_score=85.0,
        effectiveness=8.0,
    )

    # Install skill
    install_dir = temp_registry_dir / "installed"
    success = registry.install_skill("install-test", install_dir)

    assert success
    assert (install_dir / "SKILL.md").exists()
    assert (install_dir / "scripts").exists()
    assert not (install_dir / "evaluation.json").exists()  # Evaluation metadata not installed


def test_git_skill_registry_rate_skill(temp_registry_dir, sample_skill_dir):
    """Test rating a skill."""
    registry = GitSkillRegistry(
        "https://github.com/test/skills.git",
        temp_registry_dir,
    )

    metadata = SkillMetadata(
        id="rate-test",
        name="Rate Test",
        description="Test",
        domain="test",
        role="dev",
        latest_version="1.0",
    )

    registry.publish_skill(
        sample_skill_dir,
        metadata,
        quality_score=85.0,
        effectiveness=8.0,
    )

    # Rate skill
    success = registry.rate_skill("rate-test", 5.0)
    assert success

    # Check rating was updated
    index = registry.load_index()
    assert index.skills["rate-test"].rating > 0


def test_skill_metadata_versions(temp_registry_dir, sample_skill_dir):
    """Test skill versioning."""
    registry = GitSkillRegistry(
        "https://github.com/test/skills.git",
        temp_registry_dir,
    )

    # Publish v1.0
    metadata = SkillMetadata(
        id="versioned-skill",
        name="Versioned Skill",
        description="Test",
        domain="test",
        role="dev",
        latest_version="1.0",
    )

    registry.publish_skill(
        sample_skill_dir,
        metadata,
        quality_score=85.0,
        effectiveness=8.0,
    )

    # Publish v1.1
    metadata.latest_version = "1.1"
    registry.publish_skill(
        sample_skill_dir,
        metadata,
        quality_score=88.0,
        effectiveness=8.5,
    )

    # Check both versions exist
    index = registry.load_index()
    skill = index.skills["versioned-skill"]
    assert "1.0" in skill.versions
    assert "1.1" in skill.versions
    assert skill.latest_version == "1.1"
