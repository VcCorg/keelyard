"""Devin CLI execution adapter — headless sessions via the local `devin` CLI.

Unlike the ``devin`` cloud-API engine (which the backend drives over REST), this
runs through the developer's **locally installed, locally authenticated** ``devin``
CLI — inheriting its config/provisioning — and executes **headless** (no IDE
window). The session command is configurable (``DEVIN_CLI_SESSION_CMD``) because
the exact CLI verb varies by Devin version; a best-guess default is provided.
"""
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from typing import Optional

from agentic_cli.execution.base import EngineInfo, ExecutionResult, ExecutionSpec

# Command template. Placeholders: {prompt} {title} {jira} {domain} {bundle}
ENV_CLI_CMD = "DEVIN_CLI_SESSION_CMD"
DEFAULT_CLI_CMD = "devin cloud session create --prompt {prompt}"

_SESSION_ID_RE = re.compile(
    r"""session[ _-]?id["']?\s*[:=]\s*["']?([A-Za-z0-9][A-Za-z0-9_-]{3,})""",
    re.IGNORECASE,
)


class _SafeDict(dict):
    def __missing__(self, key):  # leave unknown placeholders untouched
        return "{" + key + "}"


def parse_session_id(output: str) -> Optional[str]:
    m = _SESSION_ID_RE.search(output or "")
    return m.group(1) if m else None


def _cli_present() -> bool:
    return shutil.which("devin") is not None


class DevinCliEngine:
    name = "devin-cli"

    def info(self) -> EngineInfo:
        present = _cli_present()
        cmd = os.environ.get(ENV_CLI_CMD, DEFAULT_CLI_CMD)
        return EngineInfo(
            name=self.name,
            available=present,
            kind="cli",
            description="Devin CLI — headless sessions via your local devin CLI (no IDE)",
            detail=(f"runs `{cmd.split(' ')[0]} …` (set {ENV_CLI_CMD} to customize)"
                    if present else "the `devin` CLI is not on PATH"),
            supports_ask=False,
        )

    def _render_command(self, spec: ExecutionSpec, bundle_path: str) -> list[str]:
        template = os.environ.get(ENV_CLI_CMD, DEFAULT_CLI_CMD)
        vals = _SafeDict(
            prompt=spec.prompt, title=spec.title or spec.prompt[:80],
            jira=spec.jira, domain=spec.domain, bundle=bundle_path or "")
        return [part.format_map(vals) for part in shlex.split(template)]

    def create_session(self, spec: ExecutionSpec) -> ExecutionResult:
        from agentic_cli.execution.local_adapter import LocalContextEngine

        # Produce the SAME governed context bundle any engine gets; the CLI reads it.
        local = LocalContextEngine().create_session(
            ExecutionSpec(prompt=spec.prompt, title=spec.title, jira=spec.jira,
                          domain=spec.domain, tags=list(spec.tags),
                          context=list(spec.context), dry_run=spec.dry_run))
        bundle_path = (local.raw or {}).get("path") or local.url or ""
        cmd = self._render_command(spec, bundle_path)

        if spec.dry_run:
            return ExecutionResult(
                engine=self.name, status="preview", is_new=True, dry_run=True,
                raw={"command": " ".join(cmd), "bundle_path": bundle_path,
                     "instructions": f"Would run headless: {' '.join(cmd)}"})

        if not _cli_present():
            raise RuntimeError("The `devin` CLI is not installed / not on PATH.")

        # Launch headless in the background — a coding session may run for a while;
        # we don't block the request or open an IDE. Track it in Devin's dashboard.
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"Failed to launch the Devin CLI: {e}") from e

        return ExecutionResult(
            engine=self.name, status="launched", is_new=True, dry_run=False,
            raw={"command": " ".join(cmd), "bundle_path": bundle_path,
                 "instructions": "Running headless via the Devin CLI (background) — "
                                 "no IDE opened. Track progress in your Devin dashboard."})

    def get_status(self, session_id: str) -> Optional[str]:
        return None
