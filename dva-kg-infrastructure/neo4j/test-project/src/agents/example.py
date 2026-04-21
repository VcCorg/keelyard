"""Example ADK agent implementation."""

import logging
from typing import Any, Dict
from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class ExampleAgent(BaseAgent):
    """
    Example agent demonstrating ADK agent patterns.
    
    This agent processes text input and returns structured responses.
    Replace this with your actual agent implementation.
    """

    def __init__(self, model: str = "gpt-4", **kwargs):
        """
        Initialize the example agent.

        Args:
            model: Model to use for processing
            **kwargs: Additional configuration
        """
        super().__init__(model=model, **kwargs)
        self.name = "ExampleAgent"
        logger.info(f"Initialized {self.name}")

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input data and return results.

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

        logger.info(f"Processing input: {text[:50]}...")

        # Add to history
        self.add_to_history({
            "type": "process",
            "input": text,
            "model": self.model,
        })

        # Simulate processing (replace with actual ADK agent logic)
        result = await self._process_with_model(text)

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
            "metadata": {
                "input_length": len(text),
                "output_length": len(result),
                "temperature": self.temperature,
            },
        }

    async def _process_with_model(self, text: str) -> str:
        """
        Process text with the configured model.
        
        This is a placeholder. Replace with actual ADK agent API calls.

        Args:
            text: Input text to process

        Returns:
            Processed text
        """
        # TODO: Replace with actual ADK agent implementation
        # Example:
        # response = await adk_client.complete(
        #     model=self.model,
        #     prompt=text,
        #     temperature=self.temperature,
        #     max_tokens=self.max_tokens
        # )
        # return response.text

        # Placeholder response
        return f"Processed by {self.model}: {text.upper()}"

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
