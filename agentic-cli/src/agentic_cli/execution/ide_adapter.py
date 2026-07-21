"""IDE execution adapters — local editor + assistant handoff (no cloud session).

An IDE assistant (VS Code + GitHub Copilot, Cursor, JetBrains AI) isn't a remote
session you launch via an API — it's a *local* assistant. So behind the neutral
seam, ``create_session`` for an IDE engine **prepares the governed context
bundle** (delegating to the local engine, so governance/audit are identical) and
returns a **handoff**: where the bundle is and how to open it in the editor. This
keeps the abstraction honest — cloud engines run remotely; IDE engines hand off
governed context to the human's editor.
"""
from __future__ import annotations

from typing import Optional

from agentic_cli.execution.base import EngineInfo, ExecutionResult, ExecutionSpec


class VSCodeCopilotEngine:
    """VS Code + GitHub Copilot handoff engine."""

    name = "vscode-copilot"
    _label = "VS Code + GitHub Copilot"

    def info(self) -> EngineInfo:
        return EngineInfo(
            name=self.name,
            available=True,          # a handoff needs no credentials
            kind="ide",
            description=f"{self._label} — local IDE handoff with governed context",
            detail="prepares a context bundle to open in VS Code",
            supports_ask=False,      # can't be queried headlessly — ask in the IDE
        )

    def create_session(self, spec: ExecutionSpec) -> ExecutionResult:
        from agentic_cli.execution.local_adapter import LocalContextEngine

        # Reuse the local engine so the SAME governed bundle is produced and the
        # launch is audited identically — the IDE just consumes it locally.
        local = LocalContextEngine().create_session(spec)
        bundle_path = local.url
        instructions = (
            f"1. Open your repository in {self._label.split(' + ')[0]}.\n"
            f"2. Load the governed context bundle (CONTEXT.md) at {bundle_path}.\n"
            "3. Use Copilot Chat with that context as your working brief."
        )
        vscode_uri = (f"vscode://file/{bundle_path}"
                      if bundle_path and not spec.dry_run else None)
        return ExecutionResult(
            engine=self.name,
            session_id=local.session_id,
            url=vscode_uri or bundle_path,
            status="preview" if spec.dry_run else "handoff",
            is_new=True,
            dry_run=spec.dry_run,
            raw={**(local.raw or {}), "handoff": self.name,
                 "bundle_path": bundle_path, "instructions": instructions},
        )

    def get_status(self, session_id: str) -> Optional[str]:
        # A handoff has no remote lifecycle to poll.
        return None
