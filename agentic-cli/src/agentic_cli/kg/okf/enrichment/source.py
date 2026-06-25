"""Pluggable concept source interface (ported from the GCP OKF agent).

A `Source` advertises the concepts it knows about (`list_concepts`) and yields
raw, structured metadata for each (`read_concept`). The enrichment runner turns
that metadata into conformant OKF concept documents.

The interface is intentionally tiny so new sources (codebase, Confluence, Jira,
Neo4j export) can be added without touching the runner.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConceptRef:
    """A pointer to one concept a source can describe.

    `id` is a path-like tuple, e.g. ("modules", "auth_service") or
    ("features", "cwow-27901"). It maps directly to the OKF concept path
    (`<id...>.md`) so concept IDs derive from the file path per OKF §2.
    """

    id: tuple[str, ...]
    type: str
    resource: str | None = None
    hint: dict[str, Any] = field(default_factory=dict)

    @property
    def id_str(self) -> str:
        return "/".join(self.id)


class Source(ABC):
    """Abstract metadata source that the enrichment runner reads from."""

    name: str = "source"

    @abstractmethod
    def list_concepts(self) -> list[ConceptRef]:
        """Enumerate every concept this source can describe."""
        raise NotImplementedError

    @abstractmethod
    def read_concept(self, ref: ConceptRef) -> dict[str, Any]:
        """Return raw structured metadata for one concept.

        The returned dict is handed to the LLM verbatim (as JSON) to seed the
        OKF document body, so keep keys human-meaningful.
        """
        raise NotImplementedError

    def sample(self, ref: ConceptRef, n: int = 5) -> list[dict[str, Any]] | None:
        """Optional concrete examples (rows, snippets). Default: none."""
        return None
