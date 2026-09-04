"""Domain onboarding: capture intent, review it, score what it adds up to.

The pipeline this package implements:

    add-docs  →  extract  →  [human review]  →  finalize  →  score

- :mod:`classify`   — what a tracked doc is *for*, so the onboarding guide is not
  weighted like a meeting note.
- :mod:`extract`    — reduce a body to instruction candidates in memory, and
  discard it.
- :mod:`redaction`  — what must never reach a git-visible file.
- :mod:`proposal`   — the reviewable worklist; nothing lands unreviewed.
- :mod:`provenance` — whether a context file carries content or filler.
- :mod:`readiness`  — could a new teammate ship from this?
"""

from agentic_cli.onboarding import (  # noqa: F401
    classify,
    extract,
    proposal,
    provenance,
    readiness,
    redaction,
)

__all__ = [
    "classify", "extract", "proposal", "provenance", "readiness", "redaction",
]
