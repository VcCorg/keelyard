"""Evaluation service — thin proxy over the agentic-cli `eval` commands.

Reads import the CLI's module-level managers directly (single source of truth
for the ~/.agentic-cli/* stores). Long-running steps (run agent, compare,
create config, generate report) shell out to the real `keel eval ...` CLI and
stream output, so all evaluation logic lives in exactly one place.
"""

import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import AsyncGenerator, Optional

from pydantic import BaseModel

# Directory where HTML reports are written so the dashboard can serve them.
REPORTS_DIR = Path.home() / ".agentic-cli" / "dashboard-reports"


# ── Pydantic models (transport shapes only) ─────────────────────────────────

class EvalConfigInfo(BaseModel):
    name: str
    dataset: str
    metrics: list[str] = []
    framework: str = "builtin"
    judge: str = "none"
    llm_model: Optional[str] = None
    description: str = ""
    created: Optional[str] = None
    updated: Optional[str] = None


class DatasetInfo(BaseModel):
    name: str
    versions: list[int] = []
    latest: Optional[int] = None


class EvalRunInfo(BaseModel):
    eval_id: str
    eval_name: str
    agent: str
    dataset: str
    dataset_version: Optional[int] = None
    framework: str = ""
    judge: str = ""
    metrics: list[str] = []
    timestamp: str = ""
    num_rows: int = 0
    aggregate: dict[str, float] = {}
    overall_score: float = 0.0


class MetricInfo(BaseModel):
    name: str
    kind: str  # "builtin" | "custom"
    description: str = ""


# ── CLI access helpers ──────────────────────────────────────────────────────

def _eval_mod():
    """Import the CLI eval command module (holds the module-level managers)."""
    from agentic_cli.commands import eval as eval_cmd
    return eval_cmd


def resolve_cli_command() -> list[str]:
    keel = shutil.which("keel")
    if keel:
        return [keel]
    return [sys.executable, "-m", "agentic_cli.main"]


# ── Reads (library import) ──────────────────────────────────────────────────

def list_frameworks() -> list[str]:
    from agentic_cli.evaluation.frameworks import list_frameworks as _lf
    return _lf()


def list_eval_configs() -> list[EvalConfigInfo]:
    configs = _eval_mod().config_manager.list() or []
    return [
        EvalConfigInfo(
            name=c.name,
            dataset=c.dataset,
            metrics=c.metrics or [],
            framework=c.framework,
            judge=c.judge,
            llm_model=c.llm_model,
            description=c.description or "",
            created=c.created,
            updated=c.updated,
        )
        for c in configs
    ]


def list_datasets() -> list[DatasetInfo]:
    mapping = _eval_mod().csv_manager.list_datasets() or {}
    out: list[DatasetInfo] = []
    for name, versions in mapping.items():
        vs = sorted(versions)
        out.append(DatasetInfo(name=name, versions=vs, latest=vs[-1] if vs else None))
    return sorted(out, key=lambda d: d.name)


def list_runs(eval_name: Optional[str] = None) -> list[EvalRunInfo]:
    store = _eval_mod().result_store
    runs = store.for_eval(eval_name) if eval_name else store.list()
    return [
        EvalRunInfo(
            eval_id=r.eval_id,
            eval_name=r.eval_name,
            agent=r.agent,
            dataset=r.dataset,
            dataset_version=r.dataset_version,
            framework=r.framework,
            judge=r.judge,
            metrics=r.metrics or [],
            timestamp=r.timestamp,
            num_rows=r.num_rows,
            aggregate=r.aggregate or {},
            overall_score=round(r.overall_score(), 4),
        )
        for r in (runs or [])
    ]


def list_metrics() -> list[MetricInfo]:
    out: list[MetricInfo] = []
    try:
        from agentic_cli.evaluation.metrics import get_all_metrics
        for name, m in (get_all_metrics() or {}).items():
            out.append(MetricInfo(
                name=name,
                kind="builtin",
                description=getattr(m, "description", "") or "",
            ))
    except Exception:
        pass
    try:
        for cm in (_eval_mod().custom_metric_manager.list() or []):
            out.append(MetricInfo(
                name=cm.name,
                kind="custom",
                description=getattr(cm, "description", "") or getattr(cm, "prompt", "")[:120],
            ))
    except Exception:
        pass
    return out


# ── Long-running steps (subprocess + streaming) ─────────────────────────────

class CommandResult(BaseModel):
    success: bool
    output: str


def _run_cli(args: list[str]) -> CommandResult:
    cmd = resolve_cli_command() + ["eval"] + args
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
    output = ((proc.stdout or "") + (proc.stderr or "")).strip()
    return CommandResult(success=proc.returncode == 0, output=output)


def create_eval_config(
    name: str,
    dataset: str,
    metrics: list[str],
    framework: str = "builtin",
    judge: str = "none",
    llm_model: Optional[str] = None,
    description: str = "",
    force: bool = False,
) -> CommandResult:
    """Create an eval config by shelling out to `keel eval create` (reuses validation)."""
    args = ["create", name, dataset, "--metrics", ",".join(metrics), "--framework", framework, "--judge", judge]
    if llm_model:
        args += ["--llm", llm_model]
    if description:
        args += ["--description", description]
    if force:
        args += ["--force"]
    return _run_cli(args)


def report_output_path(eval_name: str) -> Path:
    """Deterministic on-disk path for an eval's generated HTML report."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in eval_name)
    return REPORTS_DIR / f"{safe}.html"


def report_exists(eval_name: str) -> bool:
    return report_output_path(eval_name).exists()


async def stream_eval_command(args: list[str]) -> AsyncGenerator[str, None]:
    """Run `keel eval <args>` and yield stdout/stderr lines as they arrive."""
    cmd = resolve_cli_command() + ["eval"] + args
    yield f"$ {' '.join(cmd)}"

    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
    )

    assert proc.stdout is not None
    while True:
        raw = await proc.stdout.readline()
        if not raw:
            break
        yield raw.decode(errors="replace").rstrip("\n")

    rc = await proc.wait()
    yield f"__EXIT__ {rc}"
