"""Skill content generation and enrichment."""

from pathlib import Path
from typing import Any, Optional

from agentic_cli.analyzer.detector import ProjectAnalysis
from agentic_cli.agents.onboard.models import init_model
from agentic_cli.agents.onboard.prompts import get_prompts


def generate_skill_content(
    skill_name: str,
    description: str,
    tags: list[str],
    reason: str,
    model: Optional[Any] = None,
    prompts: Optional[dict[str, str]] = None,
) -> str:
    """Generate SKILL.md content for a proposed skill.

    Args:
        skill_name: Kebab-case skill name.
        description: Short description.
        tags: Relevant tags.
        reason: Why this skill was proposed.
        model: Optional pre-initialized model.
        prompts: Optional prompt overrides dict.

    Returns:
        Complete SKILL.md content string.
    """
    if model is None:
        model = init_model()

    prompt_templates = get_prompts(prompts)

    prompt = prompt_templates["skill_content"].format(
        skill_name=skill_name,
        description=description,
        tags=", ".join(tags),
        reason=reason,
    )

    try:
        response = model.generate_content(prompt)
        content = response.text.strip()
        if content.startswith("```") and content.endswith("```"):
            content = content.split("\n", 1)[1]
            content = content[:content.rindex("```")]
        return content.strip()
    except Exception as e:
        return f"""---
name: {skill_name}
description: >-
  {description}
---

# {skill_name.replace('-', ' ').title()}

> Auto-generated skill proposal. Content generation failed: {e}
> Please fill in manually.

## Guidelines

- TODO: Add guidelines for {skill_name}
"""


def enrich_skill_with_context(
    skill_path: Path,
    analysis: ProjectAnalysis,
    model: Optional[Any] = None,
    prompts: Optional[dict[str, str]] = None,
) -> str | None:
    """Enrich an existing skill with project-specific context.

    Args:
        skill_path: Path to the SKILL.md file.
        analysis: Project analysis results.
        model: Optional pre-initialized model.
        prompts: Optional prompt overrides dict.

    Returns:
        Updated SKILL.md content, or None on failure.
    """
    if not skill_path.exists():
        return None

    current_content = skill_path.read_text()

    if "## Project-Specific Notes" in current_content:
        return None

    if model is None:
        model = init_model()

    prompt_templates = get_prompts(prompts)

    prompt = prompt_templates["skill_enrichment"].format(
        current_content=current_content,
        languages=", ".join(analysis.languages),
        frameworks=", ".join(analysis.frameworks),
        dependencies=", ".join(analysis.dependencies[:30]),
        source_patterns=", ".join(analysis.source_patterns) if analysis.source_patterns else "None detected",
    )

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"[WARNING] Skill enrichment failed: {e}")
        return None
