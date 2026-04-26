"""Tests for agent adapters."""

import asyncio

import pytest

from agentic_cli.evaluation.agent_adapters import AgentAdapter, MockAgents


@pytest.mark.asyncio
async def test_agent_adapter_wrap_sync():
    """Test wrapping a sync function to async."""

    def sync_agent(input_text: str) -> str:
        return f"Echo: {input_text}"

    async_agent = AgentAdapter.wrap_sync(sync_agent)

    result = await async_agent("hello")
    assert result == "Echo: hello"


@pytest.mark.asyncio
async def test_agent_adapter_ensure_async_with_sync():
    """Test ensure_async with sync function."""

    def sync_fn(text: str) -> str:
        return text.upper()

    async_fn = AgentAdapter.ensure_async(sync_fn)
    assert asyncio.iscoroutinefunction(async_fn)

    result = await async_fn("hello")
    assert result == "HELLO"


@pytest.mark.asyncio
async def test_agent_adapter_ensure_async_with_async():
    """Test ensure_async with already async function."""

    async def already_async(text: str) -> str:
        return text.lower()

    result_fn = AgentAdapter.ensure_async(already_async)
    assert result_fn is already_async

    result = await result_fn("HELLO")
    assert result == "hello"


@pytest.mark.asyncio
async def test_mock_agents_simple_echo():
    """Test simple echo mock agent."""
    result = await MockAgents.simple_echo("test input")
    assert result == "test input"


@pytest.mark.asyncio
async def test_mock_agents_simple_qa():
    """Test simple QA mock agent."""
    # Test known question
    result = await MockAgents.simple_qa("what is python")
    assert "Python" in result

    # Test unknown question
    result = await MockAgents.simple_qa("unknown question xyz")
    assert "don't know" in result.lower()


@pytest.mark.asyncio
async def test_mock_agents_helpful():
    """Test helpful mock agent."""
    # Test with empty input
    result = await MockAgents.helpful_agent("")
    assert "Please provide" in result

    # Test with Python question
    result = await MockAgents.helpful_agent("What about Python?")
    assert "Python" in result

    # Test with help request
    result = await MockAgents.helpful_agent("How to get started?")
    assert "Happy to help" in result or "help" in result.lower()


def test_mock_agents_get_agent():
    """Test getting mock agents by type."""
    simple = MockAgents.get_agent("simple")
    assert callable(simple)
    assert asyncio.iscoroutinefunction(simple)

    qa = MockAgents.get_agent("qa")
    assert callable(qa)
    assert asyncio.iscoroutinefunction(qa)

    helpful = MockAgents.get_agent("helpful")
    assert callable(helpful)
    assert asyncio.iscoroutinefunction(helpful)

    # Test default
    default = MockAgents.get_agent("nonexistent")
    assert default is MockAgents.simple_echo


@pytest.mark.asyncio
async def test_mock_agents_processing_time():
    """Test that mock agents have realistic processing time."""
    import time

    start = time.time()
    await MockAgents.simple_qa("test")
    elapsed = time.time() - start

    # Should take at least the simulated delay (0.2s)
    assert elapsed >= 0.15


@pytest.mark.asyncio
async def test_multiple_mock_agents_concurrent():
    """Test running multiple mock agents concurrently."""
    agents = [
        MockAgents.simple_echo("input1"),
        MockAgents.simple_qa("what is python"),
        MockAgents.helpful_agent("help"),
    ]

    results = await asyncio.gather(*agents)
    assert len(results) == 3
    assert all(isinstance(r, str) for r in results)
