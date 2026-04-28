"""Basic Agent implementation using Google ADK framework."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from google.adk.agents import Agent
from google.adk.tools import Tool
from google.adk.models import Model
from google.cloud import aiplatform

from ..config import settings
from ..tools.calculator import CalculatorTool
from ..tools.text_analyzer import TextAnalyzerTool
from ..tools.file_reader import FileReaderTool

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)


class BasicAgent:
    """A basic agent using Google ADK framework."""
    
    def __init__(self) -> None:
        """Initialize the basic agent."""
        self.agent: Optional[Agent] = None
        self.model: Optional[Model] = None
        self.tools: List[Tool] = []
        
        # Initialize the agent
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize the ADK agent, model, and tools."""
        try:
            # Initialize Google Cloud AI Platform
            aiplatform.init(
                project=settings.google_project_id,
                location=settings.google_location,
            )
            
            # Create the model
            self.model = Model.from_pretrained(settings.vertex_ai_model)
            
            # Create tools
            self.tools = [
                CalculatorTool(),
                TextAnalyzerTool(),
                FileReaderTool(),
            ]
            
            # Create the agent
            self.agent = Agent(
                model=self.model,
                tools=self.tools,
                name=settings.agent_name,
                description=settings.agent_description,
            )
            
            logger.info(f"Agent '{settings.agent_name}' initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            raise
    
    async def run(self, message: str) -> str:
        """Run the agent with a message.
        
        Args:
            message: The message to send to the agent
            
        Returns:
            The agent's response
        """
        if not self.agent:
            raise RuntimeError("Agent not initialized")
        
        try:
            # Run the agent
            response = await self.agent.run_async(message)
            return response.content
            
        except Exception as e:
            logger.error(f"Error running agent: {e}")
            raise
    
    def run_sync(self, message: str) -> str:
        """Run the agent synchronously.
        
        Args:
            message: The message to send to the agent
            
        Returns:
            The agent's response
        """
        return asyncio.run(self.run(message))
    
    def get_tool_names(self) -> List[str]:
        """Get the names of available tools."""
        return [tool.name for tool in self.tools]
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the agent."""
        return {
            "name": settings.agent_name,
            "description": settings.agent_description,
            "model": settings.vertex_ai_model,
            "project": settings.google_project_id,
            "location": settings.google_location,
            "tools": self.get_tool_names(),
            "configured": settings.is_configured,
        }
