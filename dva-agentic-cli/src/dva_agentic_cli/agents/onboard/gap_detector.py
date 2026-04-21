"""Skill gap detection — AI-powered analysis of project vs registry."""

from typing import Any, Optional

from dva_agentic_cli.analyzer.detector import ProjectAnalysis
from dva_agentic_cli.agents.onboard.models import init_model, parse_json_response
from dva_agentic_cli.agents.onboard.prompts import get_prompts


def detect_skill_gaps(
    analysis: ProjectAnalysis,
    installed_skills: list[str],
    registry: dict,
    model: Optional[Any] = None,
    prompts: Optional[dict[str, str]] = None,
) -> list[dict[str, Any]]:
    """Use AI to detect skill gaps not covered by the registry.

    Args:
        analysis: Static project analysis results.
        installed_skills: Names of skills already installed.
        registry: Full registry.json data.
        model: Optional pre-initialized model (uses default if None).
        prompts: Optional prompt overrides dict.

    Returns:
        List of skill-gap dicts with keys:
        skill_name, description, tags, reason, auto_detect
    """
    if model is None:
        model = init_model()

    prompt_templates = get_prompts(prompts)

    # Build context strings
    languages = ", ".join(analysis.languages) or "None detected"
    frameworks = ", ".join(analysis.frameworks) or "None detected"
    build_tools = ", ".join(analysis.build_tools) or "None detected"
    test_frameworks = ", ".join(analysis.test_frameworks) or "None detected"
    databases = ", ".join(analysis.databases) or "None detected"
    api_types = ", ".join(analysis.api_types) or "None detected"
    ci_cd = ", ".join(analysis.ci_cd) or "None detected"
    has_docker = "Yes" if analysis.has_docker else "No"
    dep_count = len(analysis.dependencies)
    source_patterns = ", ".join(analysis.source_patterns) if analysis.source_patterns else "None"

    top_deps = "\n".join(
        f"- {dep}" + (f" ({analysis.raw_dependencies.get(dep, '')})" if analysis.raw_dependencies.get(dep) else "")
        for dep in analysis.dependencies[:50]
    ) or "None"

    installed_str = "\n".join(f"- {s}" for s in installed_skills) or "None"

    all_skills = registry.get("skills", [])
    available = [s for s in all_skills if s["name"] not in installed_skills]
    available_str = "\n".join(
        f"- **{s['name']}**: {s.get('description', '')}"
        for s in available
    ) or "None"

    prompt = prompt_templates["gap_detection"].format(
        languages=languages,
        frameworks=frameworks,
        build_tools=build_tools,
        test_frameworks=test_frameworks,
        databases=databases,
        api_types=api_types,
        ci_cd=ci_cd,
        has_docker=has_docker,
        dep_count=dep_count,
        top_dependencies=top_deps,
        source_patterns=source_patterns,
        installed_skills=installed_str,
        available_skills=available_str,
    )

    try:
        response = model.generate_content(prompt)
        gaps = parse_json_response(response.text)
        if not isinstance(gaps, list):
            return []
        validated = []
        for gap in gaps:
            if isinstance(gap, dict) and "skill_name" in gap and "description" in gap:
                validated.append({
                    "skill_name": gap["skill_name"],
                    "description": gap.get("description", ""),
                    "tags": gap.get("tags", []),
                    "reason": gap.get("reason", "AI-detected skill gap"),
                    "auto_detect": gap.get("auto_detect", {}),
                })
        return validated
    except Exception as e:
        print(f"[WARNING] Skill gap detection failed: {e}")
        return []
