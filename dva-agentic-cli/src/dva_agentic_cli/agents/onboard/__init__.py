"""Onboard Agent — reusable library for AI-powered skill gap detection.

This package provides the core building blocks that can be used by:
1. The CLI directly (dva code onboard --agent)
2. The default agent shipped in dva-skills/agents/onboard/
3. Custom agent projects created via dva project create --use-case onboard

All public functions accept optional `model` and prompt overrides so that
standalone agent projects can swap models, tune prompts, and evaluate
independently without modifying this library.
"""

from dva_agentic_cli.agents.onboard.gap_detector import detect_skill_gaps
from dva_agentic_cli.agents.onboard.skill_generator import (
    generate_skill_content,
    enrich_skill_with_context,
)
from dva_agentic_cli.agents.onboard.pipeline import run_onboard_pipeline
from dva_agentic_cli.agents.onboard.models import init_model, parse_json_response

__all__ = [
    "detect_skill_gaps",
    "generate_skill_content",
    "enrich_skill_with_context",
    "run_onboard_pipeline",
    "init_model",
    "parse_json_response",
]
