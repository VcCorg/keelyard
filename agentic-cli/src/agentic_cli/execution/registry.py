"""Execution-engine registry + audited, engine-neutral launch.

Callers ask for work to run; the registry picks the engine (default configurable
via ``KEEL_EXECUTION_ENGINE``) and records the launch in the central audit trail
with the vendor attributed — so swapping engines never loses traceability.
"""

from __future__ import annotations

import os
from typing import Callable, Dict, List, Optional

from agentic_cli.execution.base import EngineInfo, ExecutionEngine, ExecutionResult, ExecutionSpec

_FACTORIES: Dict[str, Callable[[], ExecutionEngine]] = {}


def register(name: str, factory: Callable[[], ExecutionEngine]) -> None:
    _FACTORIES[name.lower()] = factory


def _default_name() -> str:
    return os.environ.get("KEEL_EXECUTION_ENGINE", "devin").lower()


def get_engine(name: Optional[str] = None) -> ExecutionEngine:
    key = (name or _default_name()).lower()
    if key not in _FACTORIES:
        raise ValueError(
            f"Unknown execution engine '{key}'. Available: {', '.join(sorted(_FACTORIES)) or '(none)'}"
        )
    return _FACTORIES[key]()


def list_engines() -> List[EngineInfo]:
    out: List[EngineInfo] = []
    for name in sorted(_FACTORIES):
        try:
            out.append(_FACTORIES[name]().info())
        except Exception:  # noqa: BLE001
            out.append(EngineInfo(name=name, available=False, detail="failed to load"))
    return out


def create_session(spec: ExecutionSpec, engine: Optional[str] = None, *,
                   source: str = "cli", actor: Optional[str] = None) -> ExecutionResult:
    """Launch a session on the selected engine and audit it (engine-neutral).

    This is the single build-governance seam for EVERY engine (Devin, local,
    future adapters): the domain's ``build_governance`` dial (or the admin
    default for domain-less specs) decides whether ungoverned sessions run
    silently (off), run tagged (warn), or are refused (enforce).
    """
    from agentic_cli.meta_repo.build_governance import check_session, enforce_or_raise

    policy = check_session(spec.domain)
    enforce_or_raise(policy, "create_session")  # raises GovernanceViolation

    eng = get_engine(engine)
    result = eng.create_session(spec)
    try:
        from agentic_cli.tracker import record_action

        details = {
            "engine": eng.name,
            "jira": spec.jira,
            "domain": spec.domain,
            "dry_run": result.dry_run,
            "url": result.url,
        }
        if policy.tagged:
            details.update(policy.audit_details())
        record_action(
            "execution", "create_session",
            entity_type="session",
            entity_id=result.session_id or spec.jira or "",
            source=source,
            actor=actor,
            status="success" if not result.dry_run else "success",
            details=details,
        )
    except Exception:  # noqa: BLE001 - never break on audit
        pass
    return result


def _register_builtins() -> None:
    from agentic_cli.execution.devin_adapter import DevinEngine
    from agentic_cli.execution.local_adapter import LocalContextEngine

    register("devin", DevinEngine)
    register("local", LocalContextEngine)


_register_builtins()
