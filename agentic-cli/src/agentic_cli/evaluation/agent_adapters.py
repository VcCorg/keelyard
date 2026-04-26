"""Agent function adapters for evaluation."""

import asyncio
from typing import Callable, Optional


class AgentAdapter:
    """Adapter for wrapping agent functions for evaluation."""

    @staticmethod
    def wrap_sync(fn: Callable) -> Callable:
        """Wrap a sync function to be async-compatible.

        Args:
            fn: Synchronous function taking input_text and returning output

        Returns:
            Async function
        """
        async def async_wrapper(input_text: str) -> str:
            # Run sync function in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, fn, input_text)
        return async_wrapper

    @staticmethod
    def ensure_async(fn: Callable) -> Callable:
        """Ensure function is async, wrapping if needed.

        Args:
            fn: Function (sync or async)

        Returns:
            Async function
        """
        if asyncio.iscoroutinefunction(fn):
            return fn
        return AgentAdapter.wrap_sync(fn)


# Built-in mock agents for testing/demo
class MockAgents:
    """Mock agent implementations for testing."""

    @staticmethod
    async def simple_echo(input_text: str) -> str:
        """Echo agent - returns input as output."""
        await asyncio.sleep(0.1)  # Simulate processing
        return input_text

    @staticmethod
    async def simple_qa(input_text: str) -> str:
        """Simple QA agent with hardcoded responses."""
        await asyncio.sleep(0.2)

        # Map common questions to answers
        qa_map = {
            "what is python": "Python is a high-level programming language.",
            "what is ai": "AI stands for Artificial Intelligence.",
            "what is ml": "ML stands for Machine Learning.",
            "what is llm": "LLM stands for Large Language Model.",
        }

        normalized = input_text.lower().strip()
        for question, answer in qa_map.items():
            if question in normalized:
                return answer

        return f"I don't know the answer to: {input_text}"

    @staticmethod
    async def helpful_agent(input_text: str) -> str:
        """More helpful agent with structured responses."""
        await asyncio.sleep(0.15)

        if not input_text.strip():
            return "Please provide a question."

        # Simple keyword-based responses
        if any(word in input_text.lower() for word in ["python", "code", "programming"]):
            return (
                "Python is a versatile programming language known for its simplicity and readability. "
                "It's widely used in data science, web development, and AI/ML applications."
            )
        elif any(word in input_text.lower() for word in ["help", "how to", "guide"]):
            return (
                "I'd be happy to help! Please provide more specific details about what you need assistance with."
            )
        else:
            return f"You asked: {input_text}. I can provide more detailed information if you ask a specific question."

    @staticmethod
    def get_agent(agent_type: str = "simple") -> Callable:
        """Get a mock agent by type.

        Args:
            agent_type: 'simple', 'qa', or 'helpful'

        Returns:
            Async agent function
        """
        agents = {
            "simple": MockAgents.simple_echo,
            "qa": MockAgents.simple_qa,
            "helpful": MockAgents.helpful_agent,
        }
        return agents.get(agent_type, MockAgents.simple_echo)
