"""Vendor-neutral execution-engine layer.

The org owns knowledge, governance, and audit; the coding engine is a swappable
provider behind this seam. Devin is the default adapter today.
"""

from agentic_cli.execution.base import (
    AskResult,
    EngineInfo,
    ExecutionEngine,
    ExecutionResult,
    ExecutionSpec,
)
from agentic_cli.execution.registry import (
    ask,
    create_session,
    get_engine,
    list_engines,
    register,
)

__all__ = [
    "AskResult",
    "EngineInfo",
    "ExecutionEngine",
    "ExecutionResult",
    "ExecutionSpec",
    "ask",
    "create_session",
    "get_engine",
    "list_engines",
    "register",
]
