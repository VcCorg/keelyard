"""Example workflows using ADK agents."""

import logging
from typing import Dict, Any
from src.agents.example import ExampleAgent
from src.tools.example_tools import calculator, text_analyzer

logger = logging.getLogger(__name__)


async def simple_workflow(input_text: str) -> Dict[str, Any]:
    """
    Simple workflow: process text with an agent.

    Args:
        input_text: Text to process

    Returns:
        Workflow results
    """
    logger.info("Starting simple workflow")

    # Initialize agent
    agent = ExampleAgent()

    # Process input
    result = await agent.process({"text": input_text})

    logger.info("Simple workflow completed")
    return {
        "workflow": "simple",
        "input": input_text,
        "output": result,
        "agent_stats": agent.get_stats(),
    }


async def multi_step_workflow(input_text: str) -> Dict[str, Any]:
    """
    Multi-step workflow: analyze, process, and summarize.

    Args:
        input_text: Text to process

    Returns:
        Workflow results with all steps
    """
    logger.info("Starting multi-step workflow")
    results = {}

    # Step 1: Analyze input
    logger.info("Step 1: Analyzing input")
    analysis = text_analyzer(input_text)
    results["step1_analysis"] = analysis

    # Step 2: Process with agent
    logger.info("Step 2: Processing with agent")
    agent = ExampleAgent()
    processing_result = await agent.process({"text": input_text})
    results["step2_processing"] = processing_result

    # Step 3: Generate summary
    logger.info("Step 3: Generating summary")
    summary_prompt = f"Summarize this: {processing_result.get('result', '')}"
    summary = await agent.process({"text": summary_prompt})
    results["step3_summary"] = summary

    # Final results
    logger.info("Multi-step workflow completed")
    return {
        "workflow": "multi_step",
        "input": input_text,
        "steps": results,
        "agent_stats": agent.get_stats(),
        "success": all(
            step.get("success", False)
            for step in [analysis, processing_result, summary]
        ),
    }


async def tool_based_workflow(task: str) -> Dict[str, Any]:
    """
    Workflow that uses tools to accomplish a task.

    Args:
        task: Task description

    Returns:
        Workflow results
    """
    logger.info(f"Starting tool-based workflow: {task}")

    agent = ExampleAgent()
    results = []

    # Example: If task involves calculation
    if "calculate" in task.lower() or any(op in task for op in ["+", "-", "*", "/"]):
        # Extract expression (simplified)
        calc_result = calculator(task)
        results.append({"tool": "calculator", "result": calc_result})

    # Example: If task involves text analysis
    if "analyze" in task.lower():
        analysis = text_analyzer(task)
        results.append({"tool": "text_analyzer", "result": analysis})

    # Process with agent
    agent_result = await agent.process({"text": task})
    results.append({"tool": "agent", "result": agent_result})

    logger.info("Tool-based workflow completed")
    return {
        "workflow": "tool_based",
        "task": task,
        "tool_results": results,
        "agent_stats": agent.get_stats(),
    }
