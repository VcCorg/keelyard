"""Factory for creating LLM provider instances."""

from typing import Optional, Union
from agentic_cli.llm.base import LLMProvider, ProviderNotConfigured, MissingProviderSDK
from agentic_cli.llm.models import ModelRegistry, get_provider_from_model_or_config
from agentic_cli.llm.providers.vertex_ai import VertexAIProvider
from agentic_cli.llm.providers.anthropic import AnthropicProvider
from agentic_cli.llm.providers.openai import OpenAIProvider


def get_llm_provider(
    model_name: Optional[str] = None,
    provider_type: Optional[str] = None,
    system_instruction: Optional[str] = None,
) -> Union[VertexAIProvider, AnthropicProvider, OpenAIProvider]:
    """Factory function to initialize the right LLM provider.

    Provider selection priority:
    1. Explicit provider_type parameter (overrides everything)
    2. Inferred from model_name (if provided)
    3. Default from config (via KGConfig or init config)
    4. Fallback to "vertex-ai"

    Args:
        model_name: Model identifier (e.g., "gemini-2.5-flash", "claude-3-5-sonnet", "gpt-4")
        provider_type: Explicit provider override ("vertex-ai", "anthropic", "openai")
        system_instruction: System prompt for the model

    Returns:
        Initialized LLM provider instance

    Raises:
        ProviderNotConfigured: If provider config is missing
        MissingProviderSDK: If required SDK is not installed
    """
    # Determine which provider to use
    detected_provider = get_provider_from_model_or_config(
        model_name=model_name,
        explicit_provider=provider_type,
        config_default=None,  # Could load from config file here
    )

    # Initialize based on provider type
    if detected_provider == "anthropic":
        return AnthropicProvider(
            model_name=model_name or "claude-3-5-sonnet-20241022",
            system_instruction=system_instruction,
        )

    elif detected_provider == "openai":
        return OpenAIProvider(
            model_name=model_name or "gpt-4",
            system_instruction=system_instruction,
        )

    elif detected_provider == "vertex-ai":
        # Load Vertex AI config
        try:
            from agentic_cli.kg.config import KGConfig
            config = KGConfig.load()
        except Exception as e:
            raise ProviderNotConfigured(
                f"Could not load Vertex AI config: {e}\n"
                "Initialize with: agent-cli init vertex-ai --project-id <ID>"
            ) from e

        return VertexAIProvider(
            model_name=model_name or config.vertex_ai_model or "gemini-2.5-flash",
            project_id=config.google_project_id,
            location=config.google_location,
            credentials_path=None,  # Use Application Default Credentials
            system_instruction=system_instruction,
        )

    else:
        raise ProviderNotConfigured(
            f"Unknown provider type: {detected_provider}\n"
            f"Supported: vertex-ai, anthropic, openai"
        )


def get_default_llm_provider(
    system_instruction: Optional[str] = None,
) -> Union[VertexAIProvider, AnthropicProvider, OpenAIProvider]:
    """Get the default configured LLM provider.

    Uses configuration from ~/.dva-agentic/config.json to determine
    which provider to use.

    Args:
        system_instruction: System prompt for the model

    Returns:
        Initialized LLM provider instance

    Raises:
        ProviderNotConfigured: If no provider is configured
    """
    return get_llm_provider(system_instruction=system_instruction)
