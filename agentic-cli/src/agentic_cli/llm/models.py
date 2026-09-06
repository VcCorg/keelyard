"""Model name detection and provider mapping."""

from typing import Optional


class ModelRegistry:
    """Registry for detecting provider from model name."""

    # Provider-specific model prefixes
    VERTEX_AI_PREFIXES = [
        "gemini-",
        "text-bison-",
    ]

    ANTHROPIC_PREFIXES = [
        "claude-",
    ]

    OPENAI_PREFIXES = [
        "gpt-",
    ]

    # Locally hosted models (Ollama / LM Studio / llama.cpp / vLLM) — routed via
    # an explicit prefix, e.g. "local:llama3.2" or "ollama:qwen2.5".
    LOCAL_PREFIXES = [
        "local:",
        "ollama:",
    ]

    # Hugging Face inference router — addressed by hub repo id behind an
    # explicit prefix, e.g. "hf:meta-llama/Llama-3.1-8B-Instruct". A prefix
    # rather than a slash heuristic: "org/name" is also how local runtimes name
    # models, so inferring from the shape would misroute them.
    HUGGINGFACE_PREFIXES = [
        "hf:",
        "huggingface:",
    ]

    # The built-in deterministic fallback (no model at all).
    TEST_MODE_NAMES = ("test-mode", "test")

    # The downloadable built-in tiny model (in-process llama.cpp).
    BUILTIN_NAMES = ("builtin", "builtin-model")

    @classmethod
    def detect_provider(cls, model_name: str) -> Optional[str]:
        """Infer provider from model name.

        Args:
            model_name: Model identifier (e.g., "gemini-2.5-flash", "claude-3-5-sonnet", "gpt-4")

        Returns:
            Provider type ("vertex-ai", "anthropic", "openai") or None if unknown
        """
        model_lower = model_name.lower()

        if model_lower in cls.TEST_MODE_NAMES:
            return "test-mode"

        if model_lower in cls.BUILTIN_NAMES:
            return "builtin"

        for prefix in cls.LOCAL_PREFIXES:
            if model_lower.startswith(prefix):
                return "local"

        for prefix in cls.HUGGINGFACE_PREFIXES:
            if model_lower.startswith(prefix):
                return "huggingface"

        for prefix in cls.ANTHROPIC_PREFIXES:
            if model_lower.startswith(prefix):
                return "anthropic"

        for prefix in cls.OPENAI_PREFIXES:
            if model_lower.startswith(prefix):
                return "openai"

        for prefix in cls.VERTEX_AI_PREFIXES:
            if model_lower.startswith(prefix):
                return "vertex-ai"

        return None

    @classmethod
    def is_valid_model_name(cls, model_name: str) -> bool:
        """Check if model name is recognized by any provider.

        Args:
            model_name: Model identifier to check

        Returns:
            True if model can be detected, False otherwise
        """
        return cls.detect_provider(model_name) is not None


def get_provider_from_model_or_config(
    model_name: Optional[str] = None,
    explicit_provider: Optional[str] = None,
    config_default: Optional[str] = None,
) -> str:
    """Determine provider type based on priority.

    Priority:
    1. Explicit provider parameter (if provided)
    2. Infer from model name (if provided)
    3. Default from config (if available)
    4. Fallback to "vertex-ai"

    Args:
        model_name: Model identifier to infer from
        explicit_provider: Explicitly set provider type
        config_default: Default provider from configuration

    Returns:
        Provider type string
    """
    # Explicit provider overrides everything
    if explicit_provider:
        return explicit_provider

    # Try to infer from model name
    if model_name:
        detected = ModelRegistry.detect_provider(model_name)
        if detected:
            return detected

    # Use config default
    if config_default:
        return config_default

    # Fallback
    return "vertex-ai"
