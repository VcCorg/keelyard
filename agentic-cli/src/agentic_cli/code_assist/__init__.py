"""Code-assist onboarding-IDE registry — the vendor-neutral seam for skill placement.

Companion to ``agentic_cli/execution/`` (which owns Build engines like Devin
Cloud, Devin CLI, VS Code + Copilot). This package owns the *onboarding IDE*
concept: which SKILL.md layout to use for a given code-assist tool, and where
those files land on disk so the IDE actually reads them.

Extension model mirrors ``execution/``: add a new IDE by writing one
``CodeAssistTool`` and calling ``register_tool()``; no dispatch site needs to
know about the new name.
"""

from .tools import (
    CodeAssistTool,
    ToolNotFoundError,
    detect_tool,
    get_tool,
    list_tools,
    register_tool,
    resolve_tool_name,
)

__all__ = [
    "CodeAssistTool",
    "ToolNotFoundError",
    "detect_tool",
    "get_tool",
    "list_tools",
    "register_tool",
    "resolve_tool_name",
]
