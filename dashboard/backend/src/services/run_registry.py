"""Shared registry for streamed CLI command runs (code / eval / cli console).

Each run is captured in memory with its output, status, and timing so the UI
can list run history and re-open a run's output after a page refresh — even
while it is still streaming. Output is teed to the record as it streams.
"""

import asyncio
import os
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

from pydantic import BaseModel

MAX_RUNS = 100          # keep the most recent N runs
MAX_LINES = 5000        # cap stored output lines per run


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunInfo(BaseModel):
    id: str
    kind: str               # "code" | "eval" | "cli"
    label: str              # human-friendly summary, e.g. "onboard repo"
    command: str            # the rendered command line
    status: str             # "running" | "completed" | "failed"
    exit_code: Optional[int] = None
    created_at: str
    completed_at: Optional[str] = None
    line_count: int = 0


class RunRecord:
    def __init__(self, kind: str, label: str, command: str):
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind
        self.label = label
        self.command = command
        self.status = "running"
        self.exit_code: Optional[int] = None
        self.created_at = _now()
        self.completed_at: Optional[str] = None
        self.lines: list[str] = []

    def add_line(self, line: str) -> None:
        self.lines.append(line)
        if len(self.lines) > MAX_LINES:
            del self.lines[0 : len(self.lines) - MAX_LINES]

    def info(self) -> RunInfo:
        return RunInfo(
            id=self.id,
            kind=self.kind,
            label=self.label,
            command=self.command,
            status=self.status,
            exit_code=self.exit_code,
            created_at=self.created_at,
            completed_at=self.completed_at,
            line_count=len(self.lines),
        )


class RunRegistry:
    def __init__(self) -> None:
        self._runs: "OrderedDict[str, RunRecord]" = OrderedDict()

    def create(self, kind: str, label: str, cmd: list[str]) -> RunRecord:
        rec = RunRecord(kind=kind, label=label, command=" ".join(cmd))
        self._runs[rec.id] = rec
        while len(self._runs) > MAX_RUNS:
            self._runs.popitem(last=False)
        return rec

    def list_runs(self, kind: Optional[str] = None, limit: int = 50) -> list[RunInfo]:
        items = [r.info() for r in reversed(self._runs.values())]
        if kind:
            items = [r for r in items if r.kind == kind]
        return items[:limit]

    def get(self, run_id: str) -> Optional[RunRecord]:
        return self._runs.get(run_id)

    async def stream(self, rec: RunRecord, cmd: list[str]) -> AsyncGenerator[dict, None]:
        """Run `cmd`, tee output into `rec`, and yield SSE-style event dicts.

        Emits: {"event": "start", "data": run_id}, repeated
        {"event": "log", "data": line}, and {"event": "done", "data": code}.
        """
        yield {"event": "start", "data": rec.id}
        header = f"$ {rec.command}"
        rec.add_line(header)
        yield {"event": "log", "data": header}

        env = os.environ.copy()
        env["NO_COLOR"] = "1"
        env["TERM"] = "dumb"

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )
        except Exception as e:  # pragma: no cover - defensive
            rec.status = "failed"
            rec.exit_code = -1
            rec.completed_at = _now()
            msg = f"Failed to start command: {e}"
            rec.add_line(msg)
            yield {"event": "log", "data": msg}
            yield {"event": "done", "data": "-1"}
            return

        assert proc.stdout is not None
        try:
            while True:
                raw = await proc.stdout.readline()
                if not raw:
                    break
                line = raw.decode(errors="replace").rstrip("\n")
                rec.add_line(line)
                yield {"event": "log", "data": line}

            rec.exit_code = await proc.wait()
            rec.status = "completed" if rec.exit_code == 0 else "failed"
            rec.completed_at = _now()
            yield {"event": "done", "data": str(rec.exit_code)}
        except (asyncio.CancelledError, GeneratorExit):
            # Client disconnected — terminate the subprocess and mark the run.
            if proc.returncode is None:
                try:
                    proc.terminate()
                except ProcessLookupError:
                    pass
            rec.status = "cancelled"
            rec.completed_at = _now()
            rec.add_line("[run cancelled — client disconnected]")
            raise


# Module-level singleton shared across API routers.
registry = RunRegistry()
