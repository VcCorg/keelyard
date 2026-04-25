"""
Embedded project templates for DVA Agentic CLI.

This module provides a modular template system with:
- Framework-specific templates (ADK, LangGraph)
- Use case configurations (RAG, KG, Multi-Agent, etc.)
- Auto-selected tools based on use case
"""

from agentic_cli.templates.enums import Framework, UseCase, Tool
from agentic_cli.templates.config import TemplateConfig, USE_CASE_TOOLS
from agentic_cli.templates.generator import TemplateGenerator

__all__ = [
    "Framework",
    "UseCase", 
    "Tool",
    "TemplateConfig",
    "USE_CASE_TOOLS",
    "TemplateGenerator",
]
