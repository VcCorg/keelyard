"""Local execution adapter — renders a portable context bundle, no vendor.

This is the second engine behind the neutral seam. Given the *same*
``ExecutionSpec`` that would launch a Devin session, it instead projects the
canonical context into a portable, self-contained bundle any coding agent can
consume (Claude Code, Codex, a local script). It needs no API key, so it is
always available — the concrete proof that the org owns the context and the
engine is swappable.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from agentic_cli.execution.base import EngineInfo, ExecutionResult, ExecutionSpec

# Default workspace for rendered bundles.
CONTEXT_ROOT = Path.home() / ".keel" / "context"


class LocalContextEngine:
    name = "local"

    def info(self) -> EngineInfo:
        return EngineInfo(
            name=self.name,
            available=True,                      # no credentials required
            kind="local",
            description="Portable context bundle — engine-neutral, any coding agent",
            detail=f"writes bundles under {CONTEXT_ROOT}",
        )

    def create_session(self, spec: ExecutionSpec) -> ExecutionResult:
        from agentic_cli.context import (
            PortableContextSpec, bundle_id_for, load_governance, resolve_refs, write_bundle,
        )

        items = resolve_refs(spec.context, default_domain=spec.domain)
        pspec = PortableContextSpec(
            prompt=spec.prompt,
            title=spec.title,
            jira=spec.jira,
            domain=spec.domain,
            tags=list(spec.tags),
            items=items,
            governance=load_governance(spec.domain),
        )
        bid = bundle_id_for(pspec)
        opts = spec.engine_options or {}
        out_dir = Path(opts.get("out_dir") or (CONTEXT_ROOT / bid))

        if spec.dry_run:
            from agentic_cli.context import render_context_markdown

            preview = render_context_markdown(pspec)
            return ExecutionResult(
                engine=self.name, session_id=bid, url=str(out_dir), status="preview",
                is_new=True, dry_run=True,
                raw={"item_count": len(items),
                     "resolved": sum(1 for i in items if i.resolved),
                     "context_md": preview},
            )

        bundle = write_bundle(pspec, out_dir)
        return ExecutionResult(
            engine=self.name, session_id=bundle.bundle_id, url=str(bundle.path),
            status="prepared", is_new=True, dry_run=False,
            raw={"path": str(bundle.path), "files": bundle.files, "digest": bundle.digest,
                 "item_count": bundle.item_count, "resolved": bundle.resolved_count},
        )

    def get_status(self, session_id: str) -> Optional[str]:
        path = CONTEXT_ROOT / session_id / "manifest.json"
        return "prepared" if path.exists() else None
