"""Anthropic Claude LLM provider."""

from typing import AsyncGenerator, Optional
from agentic_cli.llm.base import LLMProvider, ProviderNotConfigured, MissingProviderSDK


class AnthropicProvider:
    """Anthropic Claude LLM provider implementation."""

    def __init__(
        self,
        model_name: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        system_instruction: Optional[str] = None,
    ):
        """Initialize Anthropic provider.

        Args:
            model_name: Claude model identifier
            api_key: Anthropic API key (or from ANTHROPIC_API_KEY env var)
            system_instruction: System prompt for the model

        Raises:
            MissingProviderSDK: If anthropic SDK is not installed
            ProviderNotConfigured: If API key is not available
        """
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise MissingProviderSDK(
                "Anthropic SDK not installed. Install with: "
                "pip install anthropic"
            ) from e

        if not api_key:
            import os
            api_key = os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            raise ProviderNotConfigured(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY env var or "
                "initialize with: agent-cli init anthropic"
            )

        self.model_name = model_name
        self.system_instruction = system_instruction
        self.client = Anthropic(api_key=api_key)

    def generate(self, prompt: str) -> str:
        """Generate text response synchronously.

        Args:
            prompt: The input prompt

        Returns:
            Generated text
        """
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=4096,
            system=self.system_instruction if self.system_instruction else None,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text

    async def generate_async(self, prompt: str) -> str:
        """Generate text response asynchronously.

        Args:
            prompt: The input prompt

        Returns:
            Generated text
        """
        from anthropic import AsyncAnthropic
        async_client = AsyncAnthropic()
        response = await async_client.messages.create(
            model=self.model_name,
            max_tokens=4096,
            system=self.system_instruction if self.system_instruction else None,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text

    async def generate_streaming(
        self,
        prompt: str
    ) -> AsyncGenerator[str, None]:
        """Stream text chunks from Claude.

        Args:
            prompt: The input prompt

        Yields:
            Text chunks as they are generated
        """
        with self.client.messages.stream(
            model=self.model_name,
            max_tokens=4096,
            system=self.system_instruction if self.system_instruction else None,
            messages=[
                {"role": "user", "content": prompt}
            ]
        ) as stream:
            for text in stream.text_stream:
                yield text

    def get_name(self) -> str:
        """Return provider/model identifier.

        Returns:
            Human-readable identifier
        """
        return f"anthropic/{self.model_name}"
