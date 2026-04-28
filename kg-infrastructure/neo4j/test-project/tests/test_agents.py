"""Tests for agent implementations."""

import pytest
from src.agents.example import ExampleAgent


@pytest.mark.asyncio
async def test_example_agent_creation():
    """Test creating an example agent."""
    agent = ExampleAgent()
    assert agent.name == "ExampleAgent"
    assert agent.model == "gpt-4"
    assert len(agent.history) == 0


@pytest.mark.asyncio
async def test_example_agent_process():
    """Test agent processing."""
    agent = ExampleAgent()
    result = await agent.process({"text": "test input"})
    
    assert result["success"] is True
    assert "result" in result
    assert result["agent"] == "ExampleAgent"
    assert len(agent.history) == 2  # process + result


@pytest.mark.asyncio
async def test_example_agent_empty_input():
    """Test agent with empty input."""
    agent = ExampleAgent()
    result = await agent.process({})
    
    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_example_agent_chat():
    """Test agent chat interface."""
    agent = ExampleAgent()
    response = await agent.chat("Hello agent!")
    
    assert isinstance(response, str)
    assert len(response) > 0


def test_agent_history():
    """Test agent history management."""
    agent = ExampleAgent()
    
    # Add some interactions
    agent.add_to_history({"type": "test", "data": "test1"})
    agent.add_to_history({"type": "test", "data": "test2"})
    
    assert len(agent.history) == 2
    
    # Get limited history
    limited = agent.get_history(limit=1)
    assert len(limited) == 1
    
    # Clear history
    agent.clear_history()
    assert len(agent.history) == 0


def test_agent_stats():
    """Test agent statistics."""
    agent = ExampleAgent(model="gpt-3.5-turbo", temperature=0.5)
    stats = agent.get_stats()
    
    assert stats["model"] == "gpt-3.5-turbo"
    assert stats["temperature"] == 0.5
    assert stats["total_interactions"] == 0
    assert "created_at" in stats
    assert "uptime_seconds" in stats


@pytest.mark.asyncio
async def test_agent_reset():
    """Test agent reset."""
    agent = ExampleAgent()
    
    # Add some history
    await agent.process({"text": "test"})
    assert len(agent.history) > 0
    
    # Reset
    agent.reset()
    assert len(agent.history) == 0
