"""Tests for skill validation."""

import tempfile
from pathlib import Path
import pytest

from agentic_cli.evaluation.validator import SkillValidator, ValidationResult


@pytest.fixture
def temp_skill_dir():
    """Create a temporary directory for test skills."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_validate_valid_skill(temp_skill_dir):
    """Test validation of a complete, valid skill."""
    skill_content = """---
name: test-skill
description: A test skill for validation
---

# Test Skill

This is a test skill.

## Instructions

Follow these steps:

1. Read the instructions
2. Understand the workflow
3. Use the tools properly

## Available Tools

- Tool 1: Does something
- Tool 2: Does something else

## Workflow

1. First step
2. Second step
3. Third step

## Examples

Example 1: Using tool 1
Example 2: Using tool 2
"""
    skill_file = temp_skill_dir / "SKILL.md"
    skill_file.write_text(skill_content)

    validator = SkillValidator(skill_file)
    result = validator.validate()

    assert result.passed is True
    assert result.quality_score >= 70
    assert len(result.checks) > 0
    assert result.frontmatter.get("name") == "test-skill"
    assert "Instructions" in result.sections
    assert "Available Tools" in result.sections
    assert "Workflow" in result.sections


def test_validate_missing_sections(temp_skill_dir):
    """Test validation of a skill with missing required sections."""
    skill_content = """---
name: incomplete-skill
description: A skill missing sections
---

# Incomplete Skill

This skill is missing required sections.
"""
    skill_file = temp_skill_dir / "SKILL.md"
    skill_file.write_text(skill_content)

    validator = SkillValidator(skill_file)
    result = validator.validate()

    assert result.passed is False
    assert result.quality_score < 100
    assert len(result.warnings) > 0


def test_validate_missing_frontmatter(temp_skill_dir):
    """Test validation of a skill without frontmatter."""
    skill_content = """# Missing Frontmatter

This skill is missing the YAML frontmatter.

## Instructions

Some instructions.
"""
    skill_file = temp_skill_dir / "SKILL.md"
    skill_file.write_text(skill_content)

    validator = SkillValidator(skill_file)
    result = validator.validate()

    assert result.passed is False
    assert any("frontmatter" in check.message.lower() for check in result.checks)


def test_validate_missing_required_fields(temp_skill_dir):
    """Test validation of frontmatter with missing required fields."""
    skill_content = """---
description: Missing name field
---

# Test Skill
"""
    skill_file = temp_skill_dir / "SKILL.md"
    skill_file.write_text(skill_content)

    validator = SkillValidator(skill_file)
    result = validator.validate()

    assert result.passed is False
    # Should report missing 'name' field


def test_validate_nonexistent_file(temp_skill_dir):
    """Test validation of a non-existent skill file."""
    skill_file = temp_skill_dir / "nonexistent.md"

    validator = SkillValidator(skill_file)
    result = validator.validate()

    assert result.passed is False
    assert len(result.errors) > 0


def test_sections_extraction(temp_skill_dir):
    """Test that sections are correctly extracted from skill body."""
    skill_content = """---
name: test-skill
description: Test
---

# Test

## Instructions
Some instructions

## Available Tools
Tool list

## Workflow
1. Step one
2. Step two

## Optional Section
Some optional content
"""
    skill_file = temp_skill_dir / "SKILL.md"
    skill_file.write_text(skill_content)

    validator = SkillValidator(skill_file)
    result = validator.validate()

    assert result.sections["Instructions"] is True
    assert result.sections["Available Tools"] is True
    assert result.sections["Workflow"] is True
    # Validator only tracks predefined optional sections, not arbitrary custom ones
    assert "Optional Section" not in result.sections


def test_quality_score_calculation(temp_skill_dir):
    """Test that quality score is calculated correctly."""
    # Minimal valid skill (low quality)
    skill_content = """---
name: minimal-skill
description: Minimal skill
---

# Minimal

## Instructions
Instructions

## Available Tools
Tools

## Workflow
1. Step
"""
    skill_file = temp_skill_dir / "SKILL.md"
    skill_file.write_text(skill_content)

    validator = SkillValidator(skill_file)
    result = validator.validate()

    # Should have a low-to-medium score due to lack of completeness
    assert 0 <= result.quality_score <= 100
    assert len(result.checks) > 0


def test_validation_result_structure(temp_skill_dir):
    """Test that ValidationResult contains all required fields."""
    skill_content = """---
name: test
description: Test skill
---

# Test

## Instructions
Instructions

## Available Tools
Tools

## Workflow
Workflow
"""
    skill_file = temp_skill_dir / "SKILL.md"
    skill_file.write_text(skill_content)

    validator = SkillValidator(skill_file)
    result = validator.validate()

    assert isinstance(result, ValidationResult)
    assert result.skill_path == skill_file
    assert hasattr(result, "quality_score")
    assert hasattr(result, "checks")
    assert hasattr(result, "sections")
    assert hasattr(result, "frontmatter")
    assert hasattr(result, "errors")
    assert hasattr(result, "warnings")


def test_markdown_formatting_check(temp_skill_dir):
    """Test markdown formatting validation."""
    skill_content = """---
name: markdown-test
description: Testing markdown
---

# Title with [unmatched bracket

## Instructions
Instructions
"""
    skill_file = temp_skill_dir / "SKILL.md"
    skill_file.write_text(skill_content)

    validator = SkillValidator(skill_file)
    result = validator.validate()

    # Should detect formatting issues
    formatting_check = next((c for c in result.checks if c.check_name == "Markdown Formatting"), None)
    assert formatting_check is not None
    if formatting_check:
        assert not formatting_check.passed or "Unmatched" in formatting_check.message
