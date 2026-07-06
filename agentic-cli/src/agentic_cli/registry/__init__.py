"""
Unified registry system for KEEL external resources.

This module provides a unified system for managing external registries:
- Skills (existing)
- Agent Templates (new)
- Agent Tools (new)
"""

from agentic_cli.registry.base import BaseRegistry, RegistryConfig
from agentic_cli.registry.manager import RegistryManager
from agentic_cli.registry.agent_template import AgentTemplateRegistry
from agentic_cli.registry.agent_tool import AgentToolRegistry

__all__ = [
    "BaseRegistry",
    "RegistryConfig", 
    "RegistryManager",
    "AgentTemplateRegistry",
    "AgentToolRegistry",
]
