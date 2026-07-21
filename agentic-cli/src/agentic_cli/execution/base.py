"""Execution-engine abstraction — the vendor-neutral seam.

The platform owns the durable layer (knowledge, governance, audit) and treats
the coding engine as a **swappable execution provider**. Everything above this
interface is engine-neutral; only the adapters below it know a specific vendor
(Devin today). Swap the adapter, keep the knowledge and orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@dataclass
class ExecutionSpec:
    """Engine-neutral description of a unit of work to run.

    ``context`` holds portable knowledge references (projected from the org
    knowledge layer). ``engine_options`` carries adapter-specific extras
    (e.g. Devin snapshot_id / playbook_id / secret_ids) so the neutral core
    never has to know them.
    """
    prompt: str
    title: str = ""
    jira: str = ""
    domain: str = ""
    tags: List[str] = field(default_factory=list)
    context: List[str] = field(default_factory=list)     # portable knowledge refs
    engine_options: Dict[str, Any] = field(default_factory=dict)
    idempotent: bool = False
    dry_run: bool = False


@dataclass
class ExecutionResult:
    engine: str
    session_id: Optional[str] = None
    url: Optional[str] = None
    status: Optional[str] = None
    is_new: bool = True
    reused: bool = False          # engine reused an existing session (idempotent hit)
    dry_run: bool = False
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AskResult:
    """Engine-neutral answer to a question about the codebase/domain.

    ``authoritative`` is False when the answer is degraded (e.g. the local
    engine fell back to the deterministic test-mode provider, or the engine
    can't be queried headlessly), so callers never present a placeholder as
    a real answer.
    """
    engine: str
    answer: str = ""
    authoritative: bool = True
    session_id: Optional[str] = None
    url: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EngineInfo:
    name: str
    available: bool
    kind: str = "cloud"          # cloud | local | ide | cli
    description: str = ""
    detail: str = ""             # e.g. why unavailable / base url
    supports_ask: bool = False   # engine can answer questions via ask()


@runtime_checkable
class ExecutionEngine(Protocol):
    """A coding-execution provider behind the neutral seam.

    ``ask`` is an optional capability (advertised via ``EngineInfo.supports_ask``)
    — an engine that can't answer questions headlessly simply omits it, and the
    registry reports the query as unsupported.
    """

    name: str

    def info(self) -> EngineInfo:
        """Report availability and metadata for this engine."""
        ...

    def create_session(self, spec: ExecutionSpec) -> ExecutionResult:
        """Start a session for the given work and return a linkable result."""
        ...

    def get_status(self, session_id: str) -> Optional[str]:
        """Best-effort current status for a session (None if unknown)."""
        ...
