"""Factory for creating LLM provider instances."""

import os
from typing import Optional, Union

from agentic_cli.llm.base import LLMProvider, ProviderNotConfigured, MissingProviderSDK
from agentic_cli.llm.models import ModelRegistry, get_provider_from_model_or_config
from agentic_cli.llm.providers.vertex_ai import VertexAIProvider
from agentic_cli.llm.providers.anthropic import AnthropicProvider
from agentic_cli.llm.providers.openai import OpenAIProvider
from agentic_cli.llm.providers.local import LocalProvider
from agentic_cli.llm.providers.local import is_configured as local_is_configured
from agentic_cli.llm.providers.test_mode import TestModeProvider

# Explicit default provider override ("vertex-ai" | "anthropic" | "openai" |
# "local" | "test-mode"). Lets a desktop install force local/test-mode.
ENV_DEFAULT_PROVIDER = "KEEL_LLM_PROVIDER"
# Set to disable the silent test-mode fallback (strict environments).
ENV_DISABLE_TEST_MODE = "KEEL_DISABLE_TEST_MODE"


def get_llm_provider(
    model_name: Optional[str] = None,
    provider_type: Optional[str] = None,
    system_instruction: Optional[str] = None,
) -> LLMProvider:
    """Return a provider that records what it generates.

    The factory is the single construction point for every model call Keel makes
    itself, which makes it the one place a generation sensor belongs. Recording
    in each caller instead would have meant remembering at every site, and the
    sites that got forgotten would be exactly the ones nobody was watching.

    The wrapper is transparent: it forwards everything it does not handle, so a
    provider gains a sensor without gaining an interface.
    """
    return _MeteredProvider(_build_provider(model_name, provider_type,
                                            system_instruction))


class _MeteredProvider:
    """Wraps a provider so every completed call lands in the ledger.

    Attribute access falls through, so a caller sees the provider it asked for.
    Only :meth:`generate` is intercepted — the async and streaming paths are
    left alone deliberately rather than half-instrumented: a streamed reply has
    no usage until the final chunk, and pretending otherwise would file a
    measured zero, which is worse than a visible gap. They are the next thing to
    do here, not something this quietly half-does.
    """

    def __init__(self, inner):
        self._inner = inner

    def __getattr__(self, name):
        return getattr(self._inner, name)

    @property
    def __class__(self):
        """Report the wrapped provider's type, so ``isinstance`` still holds.

        ``get_llm_provider`` is public API and its job is choosing a provider,
        so ``isinstance(provider, LocalProvider)`` is a fair thing for a caller
        to ask — six tests in this repo ask it, and adding a sensor should not
        silently change the answer. That break would surface far from its cause.

        The transparency is not total and pretending otherwise would be the
        worse trap: ``type(provider)`` still returns ``_MeteredProvider``. Use
        :meth:`unwrap` when the real object is what you need.
        """
        return type(self._inner)

    def unwrap(self):
        """The provider underneath, for code that needs the object itself."""
        return self._inner

    def generate(self, prompt: str) -> str:
        import time

        from agentic_cli import tracing

        # Read on this thread, before anything the provider may do with threads.
        session_id = tracing.current_session_id()
        domain = tracing.current_domain()
        phase = tracing.current_phase()
        started = time.perf_counter()
        try:
            completion = self._inner.generate(prompt)
        except Exception:
            # A failed call still consumed a round trip, and often tokens. The
            # row is what stops a flaky provider looking like an unused one.
            tracing.record_generation(
                model=_model_name(self._inner), usage=None, prompt=prompt,
                session_id=session_id, domain=domain, phase=phase, status="error",
                duration_ms=int((time.perf_counter() - started) * 1000))
            raise

        tracing.record_generation(
            model=_model_name(self._inner),
            usage=_usage_of(self._inner),
            prompt=prompt,
            completion=completion or "",
            session_id=session_id,
            domain=domain,
            phase=phase,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        return completion


def _model_name(provider) -> str:
    try:
        return provider.get_name() or ""
    except Exception:  # noqa: BLE001 - naming must not break a call
        return ""


def _usage_of(provider):
    """The provider's reported usage, or None when it does not report one."""
    reader = getattr(provider, "last_usage", None)
    if reader is None:
        return None
    try:
        return reader()
    except Exception:  # noqa: BLE001
        return None


def _build_provider(
    model_name: Optional[str] = None,
    provider_type: Optional[str] = None,
    system_instruction: Optional[str] = None,
) -> LLMProvider:
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
    # Determine which provider to use. KEEL_LLM_PROVIDER acts as the config
    # default (weaker than an explicit param or a model-name prefix).
    detected_provider = get_provider_from_model_or_config(
        model_name=model_name,
        explicit_provider=provider_type,
        config_default=os.getenv(ENV_DEFAULT_PROVIDER) or None,
    )

    # Whether the caller pinned a provider (param/prefix/env). An *implicit*
    # vertex default may fall back down the chain instead of failing hard.
    pinned = bool(
        provider_type
        or (model_name and ModelRegistry.detect_provider(model_name))
        or os.getenv(ENV_DEFAULT_PROVIDER)
    )

    # Initialize based on provider type
    if detected_provider == "test-mode":
        return TestModeProvider(model_name=model_name,
                                system_instruction=system_instruction)

    if detected_provider == "builtin":
        from agentic_cli.llm.builtin_model import BuiltinProvider

        return BuiltinProvider(model_name=model_name,
                               system_instruction=system_instruction)

    if detected_provider == "local":
        return LocalProvider(model_name=model_name,
                             system_instruction=system_instruction)

    if detected_provider == "huggingface":
        from agentic_cli.llm.providers.huggingface import HuggingFaceProvider

        # Imported lazily like the other optional backends, though this one
        # needs no SDK — the router speaks the OpenAI chat API over httpx.
        return HuggingFaceProvider(model_name=model_name,
                                   system_instruction=system_instruction)

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
        # Vertex is the implicit default. When the caller did NOT pin a
        # provider and Vertex isn't configured, fall back down the chain so a
        # fresh install (e.g. the packaged desktop app) still works:
        #   vertex → local model → downloaded built-in model → test-mode.
        try:
            from agentic_cli.kg.config import KGConfig
            config = KGConfig.load()
            if not config.google_project_id:
                raise ProviderNotConfigured("Google Cloud project not set")
            return VertexAIProvider(
                model_name=model_name or config.vertex_ai_model or "gemini-2.5-flash",
                project_id=config.google_project_id,
                location=config.google_location,
                credentials_path=None,  # Use Application Default Credentials
                system_instruction=system_instruction,
            )
        except Exception as e:
            if pinned:
                raise ProviderNotConfigured(
                    f"Could not load Vertex AI config: {e}\n"
                    "Initialize with: keel init vertex-ai --project-id <ID>"
                ) from e
            if local_is_configured():
                return LocalProvider(model_name=None,
                                     system_instruction=system_instruction)
            # Downloaded built-in tiny model (real inference, no config).
            from agentic_cli.llm import builtin_model

            if builtin_model.is_ready():
                return builtin_model.BuiltinProvider(
                    system_instruction=system_instruction)
            if not os.getenv(ENV_DISABLE_TEST_MODE):
                return TestModeProvider(system_instruction=system_instruction)
            raise ProviderNotConfigured(
                f"No LLM provider configured and test-mode is disabled: {e}\n"
                "Configure Vertex (keel init vertex-ai), a local model "
                "(keel init local-model), or unset KEEL_DISABLE_TEST_MODE."
            ) from e

    else:
        raise ProviderNotConfigured(
            f"Unknown provider type: {detected_provider}\n"
            f"Supported: vertex-ai, anthropic, openai, huggingface, local, test-mode"
        )


def get_default_llm_provider(
    system_instruction: Optional[str] = None,
) -> LLMProvider:
    """Get the default configured LLM provider.

    Uses configuration from ~/.keel-agentic/config.json to determine
    which provider to use.

    Args:
        system_instruction: System prompt for the model

    Returns:
        Initialized LLM provider instance

    Raises:
        ProviderNotConfigured: If no provider is configured
    """
    return get_llm_provider(system_instruction=system_instruction)
