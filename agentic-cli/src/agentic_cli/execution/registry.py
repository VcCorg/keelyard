"""Execution-engine registry + audited, engine-neutral launch.

Callers ask for work to run; the registry picks the engine (default configurable
via ``KEEL_EXECUTION_ENGINE``) and records the launch in the central audit trail
with the vendor attributed — so swapping engines never loses traceability.
"""

from __future__ import annotations

import os
from typing import Callable, Dict, List, Optional

from agentic_cli.execution.base import (
    AskResult, EngineInfo, ExecutionEngine, ExecutionResult, ExecutionSpec,
)

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

    # Mint the trace id BEFORE the engine runs, and bind it, so any context the
    # engine reads on the way (MCP tool calls, KG queries) lands in this
    # session's ledger rather than unattributed. The same id is the audit row's
    # correlation_id, so the session and everything it read share one key.
    from agentic_cli import tracing
    from agentic_cli.tracker import new_correlation_id

    trace_id = new_correlation_id()
    # The domain is bound alongside the trace id, and for the same reason: it
    # has to be in place before the engine runs, because the reads it makes on
    # the way in are the ones that carry the project's context cost.
    with tracing.session_scope(trace_id, domain=spec.domain):
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
            "trace_id": trace_id,
        }
        # The engine was always recorded; the model never was, so there was
        # nothing to group a "which model did better on this context?" question
        # by. Requested and served are kept apart deliberately — a request can
        # be ignored, substituted, or fall back mid-session, and attributing a
        # result to the request would silently measure the wrong thing.
        if spec.model:
            details["model_requested"] = spec.model
        if result.model:
            details["model_served"] = result.model
        if policy.tagged:
            details.update(policy.audit_details())
        record_action(
            "execution", "create_session",
            entity_type="session",
            entity_id=result.session_id or spec.jira or "",
            correlation_id=trace_id,
            source=source,
            actor=actor,
            status="success" if not result.dry_run else "success",
            details=details,
        )
    except Exception:  # noqa: BLE001 - never break on audit
        pass
    return result


def ask(spec: ExecutionSpec, engine: Optional[str] = None, *,
        source: str = "cli", actor: Optional[str] = None) -> AskResult:
    """Ask the selected engine a question about the codebase/domain (neutral).

    Read-only: unlike ``create_session`` this does not run under the build
    governance gate (it changes nothing), but it IS audited. Engines that can't
    answer headlessly (e.g. IDE handoff) are reported as unsupported rather than
    faked.
    """
    eng = get_engine(engine)
    fn = getattr(eng, "ask", None)
    if not callable(fn):
        return AskResult(
            engine=eng.name, authoritative=False,
            answer=f"The '{eng.name}' engine can't answer questions directly — "
                   "open it and ask there.")
    # Bind a trace id before the engine runs, exactly as create_session does.
    # Without this an ask's retrieval was orphaned: the reads happened, and
    # nothing tied them to the answer they produced, so the one flow that has
    # both a question and an answer could never be scored.
    from agentic_cli import tracing
    from agentic_cli.tracker import new_correlation_id

    trace_id = new_correlation_id()
    with tracing.session_scope(trace_id, domain=spec.domain):
        result: AskResult = fn(spec)
    result.trace_id = trace_id

    # The question and the answer go to the tier-two store, not the audit row.
    # Both are free text with the same disclosure profile as a retrieved
    # document, so they belong under the same cap, mask and TTL rather than in
    # a second at-rest path with its own rules. With the store off, nothing is
    # written and the session simply is not scorable — which is honest: you
    # cannot evaluate against context you chose not to keep.
    try:
        from agentic_cli import payload_store

        store = payload_store.get_store()
        store.put(spec.prompt, session_id=trace_id, source="session",
                  operation="prompt", entity_id=spec.jira or "")
        store.put(result.answer, session_id=trace_id, source="session",
                  operation="response", entity_id=spec.jira or "")
    except Exception:  # noqa: BLE001 - never break an answer over telemetry
        pass

    try:
        from agentic_cli.tracker import record_action

        record_action(
            "execution", "ask",
            entity_type="session", entity_id=result.session_id or spec.jira or "",
            correlation_id=trace_id,
            source=source, actor=actor,
            details={"engine": eng.name, "domain": spec.domain,
                     "authoritative": result.authoritative,
                     "trace_id": trace_id,
                     **({"model_requested": spec.model} if spec.model else {}),
                     **({"model_served": result.model} if result.model else {})},
        )
    except Exception:  # noqa: BLE001 - never break on audit
        pass
    return result


def _register_builtins() -> None:
    from agentic_cli.execution.devin_adapter import DevinEngine
    from agentic_cli.execution.devin_cli_adapter import DevinCliEngine
    from agentic_cli.execution.ide_adapter import VSCodeCopilotEngine
    from agentic_cli.execution.local_adapter import LocalContextEngine

    register("devin", DevinEngine)
    register("devin-cli", DevinCliEngine)
    register("local", LocalContextEngine)
    register("vscode-copilot", VSCodeCopilotEngine)


_register_builtins()
