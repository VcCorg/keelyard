"""Model initialization and response parsing utilities.

Provides a configurable model factory that standalone agents can
override with their own model provider (OpenAI, Anthropic, local, etc.).
"""

import json
from agentic_cli.config import CLI_NAME
from typing import Any, Optional, Protocol


class LLMModel(Protocol):
    """Protocol that any model must satisfy for use with the onboard agent."""

    def generate_content(self, prompt: str) -> Any:
        """Generate content from a prompt. Response must have a .text attribute."""
        ...


def init_model(
    model_name: Optional[str] = None,
    project_id: Optional[str] = None,
    location: Optional[str] = None,
) -> Any:
    """Initialize a Vertex AI GenerativeModel.

    All parameters are optional — defaults come from KGConfig.

    Args:
        model_name: Model name (default: gemini-2.5-flash-lite).
        project_id: GCP project ID (default: from KGConfig).
        location: GCP location (default: from KGConfig).

    Returns:
        A GenerativeModel instance.
    """
    from agentic_cli.kg.config import KGConfig

    config = KGConfig.load()

    pid = project_id or config.google_project_id
    loc = location or config.google_location
    name = model_name or "gemini-2.5-flash-lite"

    if not pid or not loc:
        raise ValueError(
            "Vertex AI is not configured. fRun '{CLI_NAME} init vertex-ai' first.\n"
            f"Current config: project_id={pid}, location={loc}"
        )

    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel
    except ImportError:
        raise ImportError(
            "Vertex AI packages not installed. Install with:\n"
            "  pip install agentic-cli[agent]\n"
            "  # or: pip install google-cloud-aiplatform"
        )

    vertexai.init(project=pid, location=loc)
    return GenerativeModel(name)


def parse_json_response(text: str) -> Any:
    """Parse JSON from an LLM response, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.startswith("json"):
            text = text[4:].lstrip()
        if "```" in text:
            text = text[:text.rindex("```")]
    return json.loads(text.strip())
