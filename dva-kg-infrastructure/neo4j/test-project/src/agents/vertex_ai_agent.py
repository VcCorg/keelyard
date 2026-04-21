"""Vertex AI agent implementation using Google's Gemini models."""

import logging
import os
from typing import Any, Dict, Optional

from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class VertexAIAgent(BaseAgent):
    """
    Agent using Google Vertex AI (Gemini) models.
    
    Requires google-cloud-aiplatform package and proper authentication.
    Install with: uv pip install -e ".[vertex_ai]"
    """

    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        model: str = "gemini-pro",
        credentials_path: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize Vertex AI agent.

        Args:
            project_id: Google Cloud project ID
            location: Google Cloud location/region
            model: Vertex AI model name (e.g., gemini-pro, gemini-pro-vision)
            credentials_path: Path to service account JSON key file
            **kwargs: Additional configuration
        """
        super().__init__(model=model, **kwargs)
        self.project_id = project_id
        self.location = location
        self.credentials_path = credentials_path
        self.name = "VertexAIAgent"
        
        # Set credentials if provided
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        
        # Initialize Vertex AI (lazy import to avoid dependency issues)
        self._init_vertex_ai()
        
        logger.info(
            f"Initialized {self.name} with project={project_id}, "
            f"location={location}, model={model}"
        )

    def _init_vertex_ai(self) -> None:
        """Initialize Vertex AI client."""
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
            
            vertexai.init(project=self.project_id, location=self.location)
            self.client = GenerativeModel(self.model)
            logger.info("Vertex AI initialized successfully")
        except ImportError:
            logger.error(
                "google-cloud-aiplatform not installed. "
                "Install with: uv pip install -e '.[vertex_ai]'"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            raise

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input data using Vertex AI.

        Args:
            input_data: Dictionary with 'text' or 'prompt' key

        Returns:
            Dictionary with processed results
        """
        # Extract input
        text = input_data.get("text") or input_data.get("prompt", "")
        
        if not text:
            logger.warning("No input text provided")
            return {
                "success": False,
                "error": "No input text provided",
                "agent": self.name,
            }

        logger.info(f"Processing input with Vertex AI: {text[:50]}...")

        # Add to history
        self.add_to_history({
            "type": "process",
            "input": text,
            "model": self.model,
            "provider": "vertex_ai",
        })

        try:
            # Generate content
            result = await self._generate_content(text)

            # Add result to history
            self.add_to_history({
                "type": "result",
                "output": result,
            })

            return {
                "success": True,
                "result": result,
                "agent": self.name,
                "model": self.model,
                "provider": "vertex_ai",
                "metadata": {
                    "input_length": len(text),
                    "output_length": len(result),
                    "project_id": self.project_id,
                    "location": self.location,
                },
            }
        except Exception as e:
            logger.error(f"Error processing with Vertex AI: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.name,
            }

    async def _generate_content(self, text: str) -> str:
        """
        Generate content using Vertex AI.

        Args:
            text: Input text

        Returns:
            Generated text
        """
        try:
            # Generate content (synchronous call, but wrapped in async)
            response = self.client.generate_content(
                text,
                generation_config={
                    "temperature": self.temperature,
                    "max_output_tokens": self.max_tokens,
                }
            )
            
            # Extract text from response
            if response.text:
                return response.text
            else:
                logger.warning("Empty response from Vertex AI")
                return ""
                
        except Exception as e:
            logger.error(f"Error generating content: {e}")
            raise

    async def chat(self, message: str, context: Dict[str, Any] = None) -> str:
        """
        Chat interface for the agent.

        Args:
            message: User message
            context: Optional context for the conversation

        Returns:
            Agent response
        """
        logger.info(f"Chat message: {message[:50]}...")

        # Build input with context
        input_data = {"text": message}
        if context:
            input_data["context"] = context

        # Process
        result = await self.process(input_data)

        if result["success"]:
            return result["result"]
        else:
            return f"Error: {result.get('error', 'Unknown error')}"

    def reset(self) -> None:
        """Reset the agent state."""
        self.clear_history()
        logger.info(f"Reset {self.name}")
