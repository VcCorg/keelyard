"""Tests for workflow implementations."""

import pytest
from src.workflows.example_workflow import (
    simple_workflow,
    multi_step_workflow,
    tool_based_workflow,
)


@pytest.mark.asyncio
async def test_simple_workflow():
    """Test simple workflow execution."""
    result = await simple_workflow("test input")
    
    assert result["workflow"] == "simple"
    assert "input" in result
    assert "output" in result
    assert "agent_stats" in result


@pytest.mark.asyncio
async def test_multi_step_workflow():
    """Test multi-step workflow execution."""
    result = await multi_step_workflow("test input for analysis")
    
    assert result["workflow"] == "multi_step"
    assert "steps" in result
    assert "step1_analysis" in result["steps"]
    assert "step2_processing" in result["steps"]
    assert "step3_summary" in result["steps"]
    assert isinstance(result["success"], bool)


@pytest.mark.asyncio
async def test_tool_based_workflow():
    """Test tool-based workflow."""
    result = await tool_based_workflow("analyze this text")
    
    assert result["workflow"] == "tool_based"
    assert "task" in result
    assert "tool_results" in result
    assert len(result["tool_results"]) > 0


@pytest.mark.asyncio
async def test_tool_based_workflow_with_calculation():
    """Test tool-based workflow with calculation."""
    result = await tool_based_workflow("calculate 2 + 2")
    
    assert result["workflow"] == "tool_based"
    # Should have used calculator tool
    tool_names = [tr["tool"] for tr in result["tool_results"]]
    assert "calculator" in tool_names
