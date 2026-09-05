"""Google Vertex AI LLM provider."""

from typing import AsyncGenerator, Optional
from agentic_cli.llm.base import LLMProvider, ProviderNotConfigured, MissingProviderSDK


class VertexAIProvider:
    """Vertex AI LLM provider implementation."""

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        project_id: Optional[str] = None,
        location: str = "us-central1",
        credentials_path: Optional[str] = None,
        system_instruction: Optional[str] = None,
    ):
        """Initialize Vertex AI provider.

        Args:
            model_name: Vertex AI model identifier
            project_id: Google Cloud project ID
            location: Google Cloud location/region
            credentials_path: Path to service account JSON (optional)
            system_instruction: System prompt for the model

        Raises:
            MissingProviderSDK: If vertexai SDK is not installed
            ProviderNotConfigured: If required configuration is missing
        """
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
        except ImportError as e:
            raise MissingProviderSDK(
                "Vertex AI SDK not installed. Install with: "
                "pip install google-cloud-aiplatform"
            ) from e

        if not project_id:
            raise ProviderNotConfigured(
                "Google Cloud project_id is required. "
                "Set via: agent-cli init vertex-ai --project-id <ID>"
            )

        self.model_name = model_name
        self.project_id = project_id
        self.location = location
        self.credentials_path = credentials_path
        self.system_instruction = system_instruction
        self._last_usage = None

        # Initialize Vertex AI
        if credentials_path:
            import os
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

        vertexai.init(project=project_id, location=location)

        # Create model
        self.model = GenerativeModel(
            model_name,
            system_instruction=system_instruction if system_instruction else None,
        )

    def generate(self, prompt: str) -> str:
        """Generate text response synchronously.

        Args:
            prompt: The input prompt

        Returns:
            Generated text
        """
        response = self.model.generate_content(prompt)
        self._last_usage = _usage_from(response, self.model_name)
        return response.text

    def last_usage(self):
        """What the last call consumed, as Vertex reported it."""
        return self._last_usage

    async def generate_async(self, prompt: str) -> str:
        """Generate text response asynchronously.

        Note: Vertex AI SDK doesn't have native async support,
        so this runs the sync version.

        Args:
            prompt: The input prompt

        Returns:
            Generated text
        """
        # Vertex AI SDK doesn't support async natively, so we run sync
        return self.generate(prompt)

    async def generate_streaming(
        self,
        prompt: str
    ) -> AsyncGenerator[str, None]:
        """Stream text chunks from Vertex AI.

        Uses streaming API to yield tokens as they arrive.

        Args:
            prompt: The input prompt

        Yields:
            Text chunks as they are generated
        """
        chunks = self.model.generate_content(prompt, stream=True)
        for chunk in chunks:
            if chunk.text:
                yield chunk.text

    def get_name(self) -> str:
        """Return provider/model identifier.

        Returns:
            Human-readable identifier
        """
        return f"google/{self.model_name}"


def _usage_from(response, model_name):
    """Read usage_metadata off a response, or None when it is absent."""
    from agentic_cli.llm.base import Usage

    meta = getattr(response, "usage_metadata", None)
    if meta is None:
        return None

    def _get(name):
        try:
            return int(getattr(meta, name, 0) or 0)
        except (TypeError, ValueError):
            return 0

    cached = _get("cached_content_token_count")
    found = Usage(
        input_tokens=max(_get("prompt_token_count") - cached, 0),
        output_tokens=_get("candidates_token_count"),
        cache_read_tokens=cached,
        model=model_name,
    )
    return None if found.empty else found
