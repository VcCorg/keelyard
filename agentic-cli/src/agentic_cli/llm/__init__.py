"""Language Model Provider Abstraction Layer.

This module provides a unified interface for working with different LLM providers:
- Google Vertex AI (Gemini models)
- Anthropic (Claude models)
- OpenAI (GPT models)

Usage:

    from agentic_cli.llm.factory import get_llm_provider

    # Auto-detect provider from model name
    provider = get_llm_provider(model_name="claude-3-5-sonnet")

    # Generate text synchronously
    response = provider.generate("What is Python?")

    # Stream text asynchronously
    async for chunk in provider.generate_streaming(prompt):
        print(chunk, end="", flush=True)

    # Get provider identifier
    print(provider.get_name())  # "anthropic/claude-3-5-sonnet-20241022"
"""

from agentic_cli.llm.base import (
    LLMProvider,
    ProviderNotConfigured,
    MissingProviderSDK,
    ProviderError,
)
from agentic_cli.llm.factory import get_llm_provider, get_default_llm_provider
from agentic_cli.llm.models import ModelRegistry

__all__ = [
    "LLMProvider",
    "ProviderNotConfigured",
    "MissingProviderSDK",
    "ProviderError",
    "get_llm_provider",
    "get_default_llm_provider",
    "ModelRegistry",
]
