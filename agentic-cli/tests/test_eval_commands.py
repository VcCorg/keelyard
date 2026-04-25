"""Tests for evaluation commands."""

import json
import tempfile
from pathlib import Path
from typer.testing import CliRunner

from agentic_cli.main import app

runner = CliRunner()


def test_eval_validate_skill_valid():
    """Test validating a valid skill."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_file = Path(tmpdir) / "SKILL.md"
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
        skill_file.write_text(skill_content)

        result = runner.invoke(app, ["eval", "validate-skill", str(skill_file)])
        assert result.exit_code == 0
        assert "Quality Score" in result.stdout
        assert "100" in result.stdout or "passed" in result.stdout.lower()


def test_eval_validate_skill_invalid():
    """Test validating an invalid skill."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_file = Path(tmpdir) / "SKILL.md"
        skill_content = """---
name: bad-skill
description: A
---

# Bad Skill

This is a bad skill.
"""
        skill_file.write_text(skill_content)

        result = runner.invoke(app, ["eval", "validate-skill", str(skill_file)])
        assert result.exit_code == 1
        assert "Quality Score" in result.stdout


def test_eval_validate_skill_nonexistent():
    """Test validating a non-existent skill file."""
    result = runner.invoke(
        app, ["eval", "validate-skill", "/nonexistent/path/SKILL.md"]
    )
    assert result.exit_code == 1
    assert "not found" in result.stdout.lower()


def test_eval_validate_skill_json_output():
    """Test validating skill with JSON output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_file = Path(tmpdir) / "SKILL.md"
        skill_content = """---
name: test-skill
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
        skill_file.write_text(skill_content)

        result = runner.invoke(
            app, ["eval", "validate-skill", str(skill_file), "--output", "json"]
        )
        assert result.exit_code == 0
        # Should be valid JSON
        try:
            output = json.loads(result.stdout)
            assert "skill_name" in output
            assert "quality_score" in output
            assert "checks" in output
        except json.JSONDecodeError:
            assert False, "Output is not valid JSON"


def test_eval_validate_skill_missing_sections():
    """Test validating a skill with missing required sections."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_file = Path(tmpdir) / "SKILL.md"
        skill_content = """---
name: incomplete-skill
description: Missing required sections
---

# Incomplete Skill

This skill is missing required sections.
"""
        skill_file.write_text(skill_content)

        result = runner.invoke(app, ["eval", "validate-skill", str(skill_file)])
        assert result.exit_code == 1
        assert "Missing" in result.stdout or "requires" in result.stdout.lower()


def test_eval_validate_skill_no_frontmatter():
    """Test validating a skill without YAML frontmatter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_file = Path(tmpdir) / "SKILL.md"
        skill_content = """# No Frontmatter

This skill has no YAML frontmatter.

## Instructions
Instructions
"""
        skill_file.write_text(skill_content)

        result = runner.invoke(app, ["eval", "validate-skill", str(skill_file)])
        assert result.exit_code == 1
        assert "Frontmatter" in result.stdout or "frontmatter" in result.stdout.lower()


def test_eval_validate_skill_help():
    """Test help for validate-skill command."""
    result = runner.invoke(app, ["eval", "validate-skill", "--help"])
    assert result.exit_code == 0
    assert "Validate" in result.stdout
    assert "skill" in result.stdout.lower()


def test_eval_help():
    """Test help for eval command group."""
    result = runner.invoke(app, ["eval", "--help"])
    assert result.exit_code == 0
    assert "evaluate" in result.stdout.lower() or "agent" in result.stdout.lower()
