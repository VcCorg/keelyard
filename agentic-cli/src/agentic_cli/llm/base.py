"""Base abstractions for language model providers."""

from dataclasses import dataclass
from typing import AsyncGenerator, Optional, Protocol
from typing_extensions import runtime_checkable


@dataclass(frozen=True)
class Usage:
    """What one model call actually consumed, as the provider reported it.

    Every provider SDK hands this back on the response and every provider here
    threw it away, which is why generated tokens were the one meter with nothing
    behind it at all.

    ``input_tokens`` is the *uncached* prompt. Cache reads and writes are
    reported separately by providers that support caching and are counted
    separately here, because they answer different questions: :attr:`admitted`
    is how much context the model actually saw, while the split is what a price
    table needs — a cached read is billed at a fraction of a fresh one, so
    collapsing them would make the eventual cost wrong in the direction that
    flatters us.

    ``admitted`` is also the number the ledger could never produce before. What
    Keel *retrieved* is recorded per read; what an engine *assembled* into a
    prompt — after dedup, truncation, reordering and caching — is a different
    number, and this is it, for the one path where Keel makes the call itself.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    model: str = ""

    @property
    def admitted(self) -> int:
        """Every token the model read, cached or not."""
        return self.input_tokens + self.cache_read_tokens + self.cache_write_tokens

    @property
    def empty(self) -> bool:
        return not (self.admitted or self.output_tokens)

    def to_dict(self) -> dict:
        out = {"input_tokens": self.input_tokens,
               "output_tokens": self.output_tokens}
        if self.cache_read_tokens:
            out["cache_read_tokens"] = self.cache_read_tokens
        if self.cache_write_tokens:
            out["cache_write_tokens"] = self.cache_write_tokens
        if self.model:
            out["model"] = self.model
        return out


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

    def last_usage(self) -> Optional["Usage"]:
        """What the most recent call consumed, or None when unreported.

        Optional: a provider that cannot say returns None, or omits the method
        entirely, and the caller falls back to estimating from the prompt and
        the reply. None is not a failure — a local model or a stub has no usage
        to report, and inventing one would be worse than saying so.

        Returning ``None`` rather than a zeroed :class:`Usage` is deliberate.
        Zero is a measurement, and a measured zero from a call that plainly did
        work is the kind of number that quietly suppresses a whole meter.
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
