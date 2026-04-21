"""Agent implementations."""

from src.agents.base import BaseAgent
from src.agents.example import ExampleAgent

# Vertex AI agent (optional - requires vertex_ai extras)
try:
    from src.agents.vertex_ai_agent import VertexAIAgent
    __all__ = ["BaseAgent", "ExampleAgent", "VertexAIAgent"]
except ImportError:
    __all__ = ["BaseAgent", "ExampleAgent"]
