"""Evaluation API — reads via library, long-running steps stream `keel eval ...`."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from src.services import eval_service as svc
from src.services.run_registry import registry

router = APIRouter(prefix="/api/eval", tags=["eval"])


class CreateEvalConfigRequest(BaseModel):
    name: str
    dataset: str
    metrics: list[str]
    framework: str = "builtin"
    judge: str = "none"
    llm_model: Optional[str] = None
    description: str = ""
    force: bool = False


# ── Reads ───────────────────────────────────────────────────────────────────

@router.get("/frameworks", response_model=list[str])
async def frameworks():
    try:
        return svc.list_frameworks()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configs", response_model=list[svc.EvalConfigInfo])
async def configs():
    try:
        return svc.list_eval_configs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/datasets", response_model=list[svc.DatasetInfo])
async def datasets():
    try:
        return svc.list_datasets()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs", response_model=list[svc.EvalRunInfo])
async def runs(eval_name: Optional[str] = Query(None)):
    try:
        return svc.list_runs(eval_name=eval_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=list[svc.MetricInfo])
async def metrics():
    try:
        return svc.list_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Mutations ───────────────────────────────────────────────────────────────

@router.post("/configs", response_model=svc.CommandResult)
async def create_config(req: CreateEvalConfigRequest):
    """Create an eval config (delegates validation to `keel eval create`)."""
    if not req.metrics:
        raise HTTPException(status_code=400, detail="At least one metric is required.")
    result = svc.create_eval_config(**req.model_dump())
    if not result.success:
        raise HTTPException(status_code=400, detail=result.output or "Create failed")
    return result


# ── Streaming long-running steps (SSE, recorded in run registry) ────────────

def _sse(
    kind_label: str,
    args: list[str],
    env_overrides: Optional[dict] = None,
    cwd: Optional[str] = None,
) -> EventSourceResponse:
    cmd = svc.resolve_cli_command() + ["eval"] + args
    rec = registry.create(kind="eval", label=kind_label, cmd=cmd)

    async def gen():
        async for event in registry.stream(rec, cmd, env_overrides=env_overrides, cwd=cwd):
            yield event

    return EventSourceResponse(gen())


@router.get("/run-agent/stream")
async def run_agent_stream(
    agent: str = Query(..., description="Agent spec (module:func or mock:simple|qa|helpful)"),
    eval_name: str = Query(..., description="Eval config name"),
    batch: int = Query(5, ge=1, le=20),
    project_path: Optional[str] = Query(
        None, description="Agent project path; its src/ is added to PYTHONPATH so the agent module imports"
    ),
):
    """Run `keel eval run agent <agent> <eval_name>` and stream output.

    When ``project_path`` is provided, the project's ``src`` directory is placed
    on PYTHONPATH and used as the working directory, so a generated agent's
    ``module:answer`` spec resolves without manual setup.
    """
    import os as _os
    from pathlib import Path as _Path

    env_overrides: Optional[dict] = None
    cwd: Optional[str] = None
    if project_path:
        src = _Path(project_path) / "src"
        existing = _os.environ.get("PYTHONPATH", "")
        env_overrides = {"PYTHONPATH": str(src) + (_os.pathsep + existing if existing else "")}
        cwd = project_path

    return _sse(
        f"run {eval_name} ({agent})",
        ["run", "agent", agent, eval_name, "-b", str(batch)],
        env_overrides=env_overrides,
        cwd=cwd,
    )


@router.get("/compare/stream")
async def compare_stream(
    eval_name: str = Query(...),
    compare_versions: bool = Query(False),
):
    """Run `keel eval compare <eval_name>` and stream output."""
    args = ["compare", eval_name]
    if compare_versions:
        args.append("--compare-versions")
    return _sse(f"compare {eval_name}", args)


@router.get("/report/stream")
async def report_stream(
    eval_name: str = Query(...),
):
    """Run `keel eval report generate <eval_name> -o <served-path>` and stream output."""
    out = svc.report_output_path(eval_name)
    return _sse(f"report {eval_name}", ["report", "generate", eval_name, "-o", str(out)])


@router.get("/report/exists")
async def report_status(eval_name: str = Query(...)):
    return {"exists": svc.report_exists(eval_name)}


@router.get("/report/view")
async def report_view(eval_name: str = Query(...)):
    """Serve a previously generated HTML report."""
    path = svc.report_output_path(eval_name)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report not generated yet.")
    return FileResponse(str(path), media_type="text/html")
