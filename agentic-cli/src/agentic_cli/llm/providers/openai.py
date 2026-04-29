"""OpenAI LLM provider."""

from typing import AsyncGenerator, Optional
from agentic_cli.llm.base import LLMProvider, ProviderNotConfigured, MissingProviderSDK


class OpenAIProvider:
    """OpenAI LLM provider implementation."""

    def __init__(
        self,
        model_name: str = "gpt-4",
        api_key: Optional[str] = None,
        system_instruction: Optional[str] = None,
    ):
        """Initialize OpenAI provider.

        Args:
            model_name: OpenAI model identifier
            api_key: OpenAI API key (or from OPENAI_API_KEY env var)
            system_instruction: System prompt for the model

        Raises:
            MissingProviderSDK: If openai SDK is not installed
            ProviderNotConfigured: If API key is not available
        """
        try:
            from openai import OpenAI
        except ImportError as e:
            raise MissingProviderSDK(
                "OpenAI SDK not installed. Install with: "
                "pip install openai"
            ) from e

        if not api_key:
            import os
            api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ProviderNotConfigured(
                "OpenAI API key not found. Set OPENAI_API_KEY env var or "
                "initialize with: agent-cli init openai"
            )

        self.model_name = model_name
        self.system_instruction = system_instruction
        self.client = OpenAI(api_key=api_key)

    def generate(self, prompt: str) -> str:
        """Generate text response synchronously.

        Args:
            prompt: The input prompt

        Returns:
            Generated text
        """
        response = self.client.chat.completions.create(
            model=self.model_name,
            max_tokens=4096,
            system=self.system_instruction if self.system_instruction else None,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content

    async def generate_async(self, prompt: str) -> str:
        """Generate text response asynchronously.

        Args:
            prompt: The input prompt

        Returns:
            Generated text
        """
        from openai import AsyncOpenAI
        async_client = AsyncOpenAI()
        response = await async_client.chat.completions.create(
            model=self.model_name,
            max_tokens=4096,
            system=self.system_instruction if self.system_instruction else None,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content

    async def generate_streaming(
        self,
        prompt: str
    ) -> AsyncGenerator[str, None]:
        """Stream text chunks from OpenAI.

        Args:
            prompt: The input prompt

        Yields:
            Text chunks as they are generated
        """
        with self.client.chat.completions.create(
            model=self.model_name,
            max_tokens=4096,
            stream=True,
            system=self.system_instruction if self.system_instruction else None,
            messages=[
                {"role": "user", "content": prompt}
            ]
        ) as stream:
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

    def get_name(self) -> str:
        """Return provider/model identifier.

        Returns:
            Human-readable identifier
        """
        return f"openai/{self.model_name}"
