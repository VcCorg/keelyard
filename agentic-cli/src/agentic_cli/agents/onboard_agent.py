"""Onboard Agent — backward-compatible shim.

The actual implementation lives in dva_agentic_cli.agents.onboard package.
This file re-exports everything so existing imports continue to work:

    from agentic_cli.agents.onboard_agent import run_onboard_agent
    from agentic_cli.agents.onboard_agent import detect_skill_gaps
"""

from agentic_cli.agents.onboard.models import (
    init_model as _init_model,
    parse_json_response as _parse_json_response,
)
from agentic_cli.agents.onboard.gap_detector import detect_skill_gaps
from agentic_cli.agents.onboard.skill_generator import (
    generate_skill_content,
    enrich_skill_with_context,
)
from agentic_cli.agents.onboard.pipeline import run_onboard_pipeline


def run_onboard_agent(
    analysis,
    installed_skills,
    registry,
    registry_path,
    project_path,
    enrich=False,
):
    """Backward-compatible wrapper — delegates to run_onboard_pipeline."""
    return run_onboard_pipeline(
        analysis=analysis,
        installed_skills=installed_skills,
        registry=registry,
        registry_path=registry_path,
        project_path=project_path,
        enrich=enrich,
    )


__all__ = [
    "_init_model",
    "_parse_json_response",
    "detect_skill_gaps",
    "generate_skill_content",
    "enrich_skill_with_context",
    "run_onboard_agent",
    "run_onboard_pipeline",
]
