"""Vendor-neutral execution-engine layer.

The org owns knowledge, governance, and audit; the coding engine is a swappable
provider behind this seam. Devin is the default adapter today.
"""

from agentic_cli.execution.base import (
    EngineInfo,
    ExecutionEngine,
    ExecutionResult,
    ExecutionSpec,
)
from agentic_cli.execution.registry import (
    create_session,
    get_engine,
    list_engines,
    register,
)

__all__ = [
    "EngineInfo",
    "ExecutionEngine",
    "ExecutionResult",
    "ExecutionSpec",
    "create_session",
    "get_engine",
    "list_engines",
    "register",
]
