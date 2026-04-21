"""Base agent class for all ADK agents."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all agents in the system."""

    def __init__(
        self,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ):
        """
        Initialize the base agent.

        Args:
            model: Model identifier to use
            temperature: Temperature for generation (0.0 to 2.0)
            max_tokens: Maximum tokens in response
            **kwargs: Additional configuration
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.config = kwargs
        self.history: List[Dict[str, Any]] = []
        self.created_at = datetime.now()

        logger.info(
            f"Initialized {self.__class__.__name__} with model={model}, "
            f"temperature={temperature}, max_tokens={max_tokens}"
        )

    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input data and return results.

        Args:
            input_data: Input data to process

        Returns:
            Processed results
        """
        pass

    def add_to_history(self, interaction: Dict[str, Any]) -> None:
        """
        Add an interaction to the agent's history.

        Args:
            interaction: Interaction data to store
        """
        interaction["timestamp"] = datetime.now().isoformat()
        self.history.append(interaction)
        logger.debug(f"Added interaction to history: {interaction.get('type', 'unknown')}")

    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get agent interaction history.

        Args:
            limit: Maximum number of interactions to return

        Returns:
            List of interactions
        """
        if limit:
            return self.history[-limit:]
        return self.history

    def clear_history(self) -> None:
        """Clear the agent's interaction history."""
        self.history.clear()
        logger.info("Cleared agent history")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get agent statistics.

        Returns:
            Dictionary with agent stats
        """
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "total_interactions": len(self.history),
            "created_at": self.created_at.isoformat(),
            "uptime_seconds": (datetime.now() - self.created_at).total_seconds(),
        }

    def __repr__(self) -> str:
        """String representation of the agent."""
        return (
            f"{self.__class__.__name__}(model={self.model}, "
            f"interactions={len(self.history)})"
        )
