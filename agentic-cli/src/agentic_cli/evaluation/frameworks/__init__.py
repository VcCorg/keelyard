"""Pluggable evaluation frameworks.

Use :func:`get_framework` to obtain a framework by name. The ``builtin``
framework requires no extra dependencies. Additional frameworks (e.g. ``ragas``)
are loaded lazily so their heavy dependencies remain optional.
"""

from typing import List

from agentic_cli.evaluation.frameworks.base import (
    EvalFramework,
    EvalRow,
    EvalScores,
)
from agentic_cli.evaluation.frameworks.builtin import BuiltinFramework

#: Frameworks that are always available (no optional dependencies).
_BUILTIN_FRAMEWORKS = {"builtin", "heuristic"}

#: Frameworks that require optional dependencies (loaded lazily).
_OPTIONAL_FRAMEWORKS = {"ragas"}


def list_frameworks() -> List[str]:
    """Return all known framework names (available or optional)."""
    return sorted(_BUILTIN_FRAMEWORKS | _OPTIONAL_FRAMEWORKS)


def get_framework(name: str, **kwargs) -> EvalFramework:
    """Instantiate a framework by name.

    Args:
        name: Framework name (e.g. "builtin", "ragas").
        **kwargs: Forwarded to the framework constructor (e.g. judge_type for
            builtin, llm_model for ragas).

    Returns:
        An :class:`EvalFramework` instance.

    Raises:
        ValueError: If the framework name is unknown.
        ImportError: If an optional framework's dependencies are missing.
    """
    key = (name or "builtin").lower()

    if key == "builtin":
        judge_type = kwargs.get("judge_type", "none")
        custom_metrics = kwargs.get("custom_metrics")
        return BuiltinFramework(judge_type=judge_type, custom_metrics=custom_metrics)

    if key in ("heuristic", "offline"):
        from agentic_cli.evaluation.frameworks.heuristic import HeuristicFramework

        return HeuristicFramework()

    if key == "ragas":
        try:
            from agentic_cli.evaluation.frameworks.ragas_adapter import RagasFramework
        except ImportError as e:
            raise ImportError(
                "The 'ragas' framework requires optional dependencies. "
                "Install them with: pip install 'agentic-cli[eval]'"
            ) from e
        return RagasFramework(**kwargs)

    raise ValueError(
        f"Unknown evaluation framework: '{name}'. "
        f"Available: {', '.join(list_frameworks())}"
    )


__all__ = [
    "EvalFramework",
    "EvalRow",
    "EvalScores",
    "BuiltinFramework",
    "get_framework",
    "list_frameworks",
]
