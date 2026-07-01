"""Collect agent responses for evaluation rows.

Resolving an agent to a callable is supported via:

    - ``module.path:function``  -> import and call a Python function (str -> str)
    - ``module.path:ClassName`` -> instantiate a ``BaseAgent``-style class and
      auto-wrap its ``process(dict) -> dict`` (or ``answer``/``run``/``__call__``)
      into the ``fn(str) -> str`` contract the evaluator expects
    - ``mock:<type>``           -> built-in mock agent (simple|qa|helpful)

The collector runs inputs through the agent (optionally in parallel batches)
and fills the ``response`` field of each row. Rows that already have a response
are left untouched unless ``force`` is set. Richer transports (A2A/HTTP
streaming) are added in a later phase behind this same interface.
"""

import asyncio
import importlib
import inspect
import logging
from typing import Any, Awaitable, Callable, List, Optional, Union

from agentic_cli.evaluation.agent_adapters import AgentAdapter, MockAgents
from agentic_cli.evaluation.csv_dataset import CsvRow

logger = logging.getLogger(__name__)

# An agent callable maps an input string to a response string (sync or async).
AgentCallable = Callable[[str], Union[str, Awaitable[str]]]

# Method names tried (in order) when wrapping a class-based agent that does not
# expose a ``BaseAgent``-style ``process`` method.
_STRING_ENTRYPOINTS = ("answer", "run", "__call__")
# Keys tried (in order) when extracting the response text from a ``process``
# result dict.
_RESPONSE_KEYS = ("response", "output", "text", "answer", "result")


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

    module_path, attr_name = spec.rsplit(":", 1)
    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        raise ImportError(f"Could not import agent module '{module_path}': {e}") from e

    target = getattr(module, attr_name, None)
    if target is None:
        raise ValueError(f"'{attr_name}' not found in module '{module_path}'")

    # Agent-like class (e.g. a ``BaseAgent`` subclass scaffolded by the CLI):
    # instantiate and wrap so the evaluator can call it as ``fn(str) -> str``.
    # Only classes exposing an agent entrypoint are routed here; any other class
    # object is treated as a plain callable (backward-compatible) below.
    if inspect.isclass(target) and any(
        hasattr(target, m) for m in ("process", "answer", "run")
    ):
        return _wrap_class_agent(target, f"{module_path}:{attr_name}")

    if not callable(target):
        raise ValueError(f"'{attr_name}' is not callable in module '{module_path}'")

    return AgentAdapter.ensure_async(target)


def _instantiate_agent(cls: type, spec: str) -> Any:
    """Instantiate an agent class, tolerating an optional ``settings`` arg."""
    try:
        return cls()
    except TypeError:
        # BaseAgent-style ``__init__(self, settings=None)`` already accepts no
        # args; fall back to an explicit ``settings=None`` for stricter
        # signatures before giving up.
        try:
            return cls(settings=None)
        except TypeError as e:
            raise ValueError(
                f"Could not instantiate agent class for '{spec}': {e}. "
                "Provide a module-level 'answer(input_text)->str' entrypoint "
                "or a zero-arg constructor."
            ) from e


def _extract_response(result: Any) -> str:
    """Coerce a ``process``-style result into a response string."""
    if isinstance(result, dict):
        for key in _RESPONSE_KEYS:
            if key in result and result[key] is not None:
                return str(result[key])
        return str(result)
    return str(result)


def _wrap_class_agent(cls: type, spec: str) -> AgentCallable:
    """Wrap a class-based agent into an async ``fn(str) -> str`` callable.

    Supports two shapes:

    - ``BaseAgent``-style: an async ``process(input_data: dict) -> dict`` method
      (the response text is read from common keys like ``response``), with an
      optional async ``initialize()`` invoked once before the first call.
    - A direct string entrypoint named ``answer``/``run``/``__call__`` taking
      ``input_text`` and returning a string (sync or async).
    """
    instance = _instantiate_agent(cls, spec)

    process = getattr(instance, "process", None)
    if callable(process):
        initialize = getattr(instance, "initialize", None)
        init_lock = asyncio.Lock()
        state = {"initialized": not callable(initialize)}

        async def _call_process(input_text: str) -> str:
            if not state["initialized"]:
                async with init_lock:
                    if not state["initialized"]:
                        maybe = initialize()
                        if inspect.isawaitable(maybe):
                            await maybe
                        state["initialized"] = True
            result = process({"message": input_text})
            if inspect.isawaitable(result):
                result = await result
            return _extract_response(result)

        return _call_process

    # Fall back to a direct string entrypoint.
    for name in _STRING_ENTRYPOINTS:
        entry = getattr(instance, name, None)
        if callable(entry):
            return AgentAdapter.ensure_async(entry)

    raise ValueError(
        f"Agent class for '{spec}' has no usable entrypoint. Expected an async "
        "'process(dict)->dict' method or one of "
        f"{', '.join(_STRING_ENTRYPOINTS)}."
    )


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
