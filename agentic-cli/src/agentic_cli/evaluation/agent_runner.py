"""Collect agent responses for evaluation rows.

Phase 1 supports resolving an agent to a callable via:

    - ``module.path:function``  -> import and call a Python function
    - ``mock:<type>``           -> built-in mock agent (simple|qa|helpful)

The collector runs inputs through the agent (optionally in parallel batches)
and fills the ``response`` field of each row. Rows that already have a response
are left untouched unless ``force`` is set. Richer transports (A2A/HTTP
streaming) are added in a later phase behind this same interface.
"""

import asyncio
import importlib
import logging
from typing import Awaitable, Callable, List, Optional, Union

from agentic_cli.evaluation.agent_adapters import AgentAdapter, MockAgents
from agentic_cli.evaluation.csv_dataset import CsvRow

logger = logging.getLogger(__name__)

# An agent callable maps an input string to a response string (sync or async).
AgentCallable = Callable[[str], Union[str, Awaitable[str]]]


def resolve_agent(spec: str) -> AgentCallable:
    """Resolve an agent specification into an async-compatible callable.

    Args:
        spec: One of ``module.path:function`` or ``mock:<type>``.

    Returns:
        An async callable taking ``input_text`` and returning a response.

    Raises:
        ValueError: If the spec is malformed or the target is not callable.
        ImportError: If a module path cannot be imported.
    """
    if not spec:
        raise ValueError("Agent spec must not be empty")

    if spec.startswith("mock:"):
        agent_type = spec.split(":", 1)[1] or "simple"
        return MockAgents.get_agent(agent_type)

    if ":" not in spec:
        raise ValueError(
            f"Invalid agent spec '{spec}'. Use 'module.path:function' or 'mock:<type>'."
        )

    module_path, func_name = spec.rsplit(":", 1)
    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        raise ImportError(f"Could not import agent module '{module_path}': {e}") from e

    fn = getattr(module, func_name, None)
    if fn is None or not callable(fn):
        raise ValueError(f"'{func_name}' is not a callable in module '{module_path}'")

    return AgentAdapter.ensure_async(fn)


class AgentResponseCollector:
    """Runs an agent over dataset rows to collect responses."""

    def __init__(self, agent: AgentCallable, batch_size: int = 10):
        """Initialize the collector.

        Args:
            agent: Async-compatible agent callable.
            batch_size: Max concurrent requests (clamped to 1-20).
        """
        self.agent = AgentAdapter.ensure_async(agent)
        self.batch_size = max(1, min(20, batch_size))

    async def _collect_one(self, row: CsvRow) -> None:
        """Populate a single row's response, recording errors inline."""
        try:
            row.response = str(await self.agent(row.user_input))
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(f"Agent failed for input '{row.user_input[:50]}': {e}")
            row.response = f"[ERROR] {e}"

    async def collect_async(
        self,
        rows: List[CsvRow],
        force: bool = False,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> List[CsvRow]:
        """Collect responses for rows in parallel batches.

        Args:
            rows: Rows to populate (mutated in place and returned).
            force: Re-collect even if a response already exists.
            on_progress: Optional callback ``(done, total)``.

        Returns:
            The same list of rows with responses filled.
        """
        pending = [r for r in rows if force or not r.response.strip()]
        total = len(pending)
        done = 0

        for start in range(0, total, self.batch_size):
            batch = pending[start : start + self.batch_size]
            await asyncio.gather(*(self._collect_one(r) for r in batch))
            done += len(batch)
            if on_progress:
                on_progress(done, total)

        return rows

    def collect(
        self,
        rows: List[CsvRow],
        force: bool = False,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> List[CsvRow]:
        """Synchronous wrapper around :meth:`collect_async`."""
        return asyncio.run(self.collect_async(rows, force=force, on_progress=on_progress))
