"""Base abstractions for language model providers."""

from typing import AsyncGenerator, Protocol
from typing_extensions import runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for any LLM provider - defines the interface all providers must implement."""

    def generate(self, prompt: str) -> str:
        """Generate text response (blocking call).

        Args:
            prompt: The input prompt

        Returns:
            Generated text response

        Raises:
            Exception: If generation fails
        """
        ...

    async def generate_async(self, prompt: str) -> str:
        """Generate text response asynchronously.

        Args:
            prompt: The input prompt

        Returns:
            Generated text response

        Raises:
            Exception: If generation fails
        """
        ...

    async def generate_streaming(
        self,
        prompt: str
    ) -> AsyncGenerator[str, None]:
        """Stream text chunks as they arrive.

        Args:
            prompt: The input prompt

        Yields:
            Text chunks as they are generated

        Raises:
            Exception: If generation fails
        """
        ...

    def get_name(self) -> str:
        """Return provider/model identifier for logging.

        Returns:
            Human-readable provider name (e.g., "google/gemini-2.5-flash")
        """
        ...


class ProviderNotConfigured(Exception):
    """Provider is not configured."""
    pass


class MissingProviderSDK(Exception):
    """Required provider SDK is not installed."""
    pass


class ProviderError(Exception):
    """General provider error."""
    pass
