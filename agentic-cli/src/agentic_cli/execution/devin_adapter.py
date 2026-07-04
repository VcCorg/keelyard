"""Devin execution adapter — maps the neutral seam onto Devin Cloud.

This is the *only* place that knows Devin specifics. It translates an
engine-neutral ``ExecutionSpec`` into a Devin ``SessionSpec`` (routing portable
context into Devin knowledge_ids and adapter options into snapshot/playbook/
secrets) and calls the Devin Sessions API via the existing core.
"""

from __future__ import annotations

from typing import Optional

from agentic_cli.execution.base import EngineInfo, ExecutionResult, ExecutionSpec


class DevinEngine:
    name = "devin"

    def info(self) -> EngineInfo:
        try:
            from agentic_cli.devin.config import DevinConfig, has_api_key

            cfg = DevinConfig.load()
            available = has_api_key()
            return EngineInfo(
                name=self.name,
                available=available,
                kind="cloud",
                description="Devin Cloud — autonomous coding sessions (Sessions API)",
                detail=cfg.base_url if available else "DEVIN_API_KEY not configured",
            )
        except Exception as exc:  # noqa: BLE001 - engine optional
            return EngineInfo(
                name=self.name, available=False, kind="cloud",
                description="Devin Cloud", detail=f"unavailable: {exc}",
            )

    def create_session(self, spec: ExecutionSpec) -> ExecutionResult:
        from agentic_cli.devin import SessionSpec, create_session as core_create

        opts = spec.engine_options or {}
        dspec = SessionSpec(
            prompt=spec.prompt,
            title=spec.title,
            snapshot_id=opts.get("snapshot_id"),
            playbook_id=opts.get("playbook_id"),
            knowledge_ids=list(spec.context),          # portable refs → Devin knowledge
            secret_ids=list(opts.get("secret_ids", [])),
            tags=list(spec.tags),
            idempotent=spec.idempotent,
            max_acu_limit=opts.get("max_acu_limit"),
            unlisted=bool(opts.get("unlisted", False)),
            domain=spec.domain,
            jira=spec.jira,
        )
        base_url = opts.get("base_url")
        res = (
            core_create(dspec, dry_run=spec.dry_run, base_url=base_url)
            if base_url
            else core_create(dspec, dry_run=spec.dry_run)
        )
        return ExecutionResult(
            engine=self.name,
            session_id=res.session_id,
            url=res.url,
            status=res.status,
            is_new=res.is_new,
            reused=getattr(res, "reused_local", False),
            dry_run=res.dry_run,
            raw=res.payload or {},
        )

    def get_status(self, session_id: str) -> Optional[str]:
        try:
            from agentic_cli.devin import get_session

            data = get_session(session_id)
            return data.get("status_enum") or data.get("status") if isinstance(data, dict) else None
        except Exception:  # noqa: BLE001 - best-effort
            return None
