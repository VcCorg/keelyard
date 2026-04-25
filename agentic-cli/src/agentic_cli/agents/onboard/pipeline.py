"""Onboard agent pipeline — orchestrates gap detection, content generation, and enrichment.

This is the main entry point for running the full onboard agent.
Both the CLI and standalone agent projects call this function.
"""

from pathlib import Path
from typing import Any, Optional

from agentic_cli.analyzer.detector import ProjectAnalysis
from agentic_cli.agents.onboard.gap_detector import detect_skill_gaps
from agentic_cli.agents.onboard.skill_generator import (
    generate_skill_content,
    enrich_skill_with_context,
)


def run_onboard_pipeline(
    analysis: ProjectAnalysis,
    installed_skills: list[str],
    registry: dict,
    registry_path: Path,
    project_path: Path,
    enrich: bool = False,
    model: Optional[Any] = None,
    prompts: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """Run the full onboard agent pipeline.

    1. Detect skill gaps using AI
    2. Generate SKILL.md content for each gap
    3. Optionally enrich installed skills with project context

    All AI calls share the same model and prompts, so standalone agents
    can inject their own model provider and tuned prompts.

    Args:
        analysis: Static project analysis results.
        installed_skills: Skills already installed.
        registry: Full registry.json data.
        registry_path: Path to the skills registry root.
        project_path: Path to the project being onboarded.
        enrich: Whether to enrich installed skills.
        model: Optional pre-initialized model (shared across all steps).
        prompts: Optional prompt overrides dict.

    Returns:
        Dict with keys: proposals (list), enriched (list), errors (list)
    """
    result: dict[str, Any] = {"proposals": [], "enriched": [], "errors": []}

    # Step 1: Detect gaps
    try:
        gaps = detect_skill_gaps(
            analysis, installed_skills, registry,
            model=model, prompts=prompts,
        )
    except Exception as e:
        result["errors"].append(f"Gap detection failed: {e}")
        return result

    # Step 2: Generate content for each gap
    for gap in gaps:
        try:
            content = generate_skill_content(
                skill_name=gap["skill_name"],
                description=gap["description"],
                tags=gap["tags"],
                reason=gap["reason"],
                model=model,
                prompts=prompts,
            )
            gap["content"] = content
            result["proposals"].append(gap)
        except Exception as e:
            result["errors"].append(f"Content generation failed for {gap['skill_name']}: {e}")

    # Step 3: Enrich installed skills (optional)
    if enrich:
        skills_dir = project_path / ".skills"
        for skill_name in installed_skills:
            skill_md = skills_dir / skill_name / "SKILL.md"
            if not skill_md.exists() or skill_name == "project-context":
                continue
            try:
                enriched = enrich_skill_with_context(
                    skill_md, analysis,
                    model=model, prompts=prompts,
                )
                if enriched:
                    result["enriched"].append({
                        "skill_name": skill_name,
                        "content": enriched,
                    })
            except Exception as e:
                result["errors"].append(f"Enrichment failed for {skill_name}: {e}")

    return result
