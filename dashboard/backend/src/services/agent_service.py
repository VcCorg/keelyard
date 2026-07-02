"""Agent service — reads agent state and manages lifecycle.

Hybrid approach:
- Reads: Import directly from agentic_cli modules (fast, typed)
- Mutations: Subprocess to `dva agent start/stop` (safe, consistent with CLI)
"""

import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel


AGENT_STATE_DIR = Path.home() / ".dva" / "agents"
AGENT_STATE_FILE = AGENT_STATE_DIR / "running.json"

# Project tracker DB
DVA_CONFIG_DIR = Path.home() / ".agent-cli-agentic"


class AgentInfo(BaseModel):
    """Agent instance information."""
    name: str
    status: str  # running, stopped
    pid: Optional[int] = None
    path: Optional[str] = None
    review_mode: Optional[str] = None
    poll_interval: Optional[int] = None
    log_file: Optional[str] = None
    agent_type: str = "background"  # interactive, background


class ProjectValidation(BaseModel):
    """Validation check results for a project."""
    path_exists: bool = False
    has_src: bool = False
    has_pyproject: bool = False
    has_env: bool = False
    has_domain_context: bool = False
    has_persona_skills: bool = False
    # Use-case specific
    has_mcp_clients: Optional[bool] = None
    has_sprint_manager: Optional[bool] = None
    has_standup_generator: Optional[bool] = None
    has_domain_loader: Optional[bool] = None
    has_watcher: Optional[bool] = None
    has_reviewer: Optional[bool] = None
    score: int = 0
    total: int = 0


class AgentProject(BaseModel):
    """Discovered agent project."""
    name: str
    path: str
    framework: Optional[str] = None
    use_case: Optional[str] = None
    tools: list[str] = []
    agent_type: str = "background"
    created_at: Optional[str] = None
    domain: Optional[str] = None
    validation: Optional[ProjectValidation] = None


# Interactive use cases that support chat
INTERACTIVE_USE_CASES = {"basic", "rag", "knowledge-graph", "chatbot", "code-assistant", "multi-agent", "scrum-master"}
BACKGROUND_USE_CASES = {"pr-reviewer", "onboard", "data-pipeline"}


def _is_process_running(pid: int) -> bool:
    """Check if a process with the given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _load_state() -> dict:
    """Load running agent state from file."""
    if AGENT_STATE_FILE.exists():
        try:
            return json.loads(AGENT_STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {"agents": {}}
    return {"agents": {}}


def _classify_agent_type(use_case: Optional[str]) -> str:
    """Determine if an agent is interactive or background."""
    if use_case and use_case in INTERACTIVE_USE_CASES:
        return "interactive"
    return "background"


def list_agents() -> list[AgentInfo]:
    """List all tracked agent instances with live status."""
    state = _load_state()
    agents = []
    for name, info in state.get("agents", {}).items():
        pid = info.get("pid")
        running = _is_process_running(pid) if pid else False
        agents.append(AgentInfo(
            name=name,
            status="running" if running else "stopped",
            pid=pid,
            path=info.get("path"),
            review_mode=info.get("review_mode"),
            poll_interval=info.get("poll_interval"),
            log_file=info.get("log_file"),
            agent_type=info.get("agent_type", "background"),
        ))
    return agents


def get_agent(name: str) -> Optional[AgentInfo]:
    """Get a single agent by name."""
    state = _load_state()
    info = state.get("agents", {}).get(name)
    if not info:
        return None
    pid = info.get("pid")
    running = _is_process_running(pid) if pid else False
    return AgentInfo(
        name=name,
        status="running" if running else "stopped",
        pid=pid,
        path=info.get("path"),
        review_mode=info.get("review_mode"),
        poll_interval=info.get("poll_interval"),
        log_file=info.get("log_file"),
        agent_type=info.get("agent_type", "background"),
    )


def start_agent(
    name: str,
    path: str,
    review_mode: Optional[str] = None,
    poll_interval: Optional[int] = None,
) -> AgentInfo:
    """Start an agent as a background daemon via CLI subprocess."""
    cmd = [sys.executable, "-m", "agentic_cli.main", "agent", "start", "--path", path, "--name", name]
    if review_mode:
        cmd.extend(["--review-mode", review_mode])
    if poll_interval:
        cmd.extend(["--poll-interval", str(poll_interval)])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to start agent: {result.stderr or result.stdout}")

    # Re-read state to get PID
    agent = get_agent(name)
    if agent:
        return agent
    raise RuntimeError("Agent started but not found in state")


def stop_agent(name: str) -> bool:
    """Stop a running agent."""
    state = _load_state()
    info = state.get("agents", {}).get(name)
    if not info:
        return False

    pid = info.get("pid")
    if pid and _is_process_running(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return False

    # Update state
    del state["agents"][name]
    AGENT_STATE_DIR.mkdir(parents=True, exist_ok=True)
    AGENT_STATE_FILE.write_text(json.dumps(state, indent=2))
    return True


def get_agent_logs(name: str, tail: int = 100) -> list[str]:
    """Read log lines for an agent."""
    state = _load_state()
    info = state.get("agents", {}).get(name)
    if not info:
        return []

    log_file = Path(info.get("log_file", ""))
    if not log_file.exists():
        return []

    lines = log_file.read_text().strip().split("\n")
    return lines[-tail:]


def _find_answer_module(path: str) -> Optional[str]:
    """Return the dotted module (relative to ``src/``) exposing ``answer()``.

    E.g. ``agents.orchestrator`` for ``<path>/src/agents/orchestrator.py``.
    Returns None if no agent module exposes an ``answer()`` entrypoint.
    """
    agents_dir = Path(path) / "src" / "agents"
    if not agents_dir.exists():
        return None
    for py in sorted(agents_dir.glob("*.py")):
        if py.name in ("__init__.py", "base.py"):
            continue
        try:
            text = py.read_text()
        except OSError:
            continue
        if "def answer(" in text:
            return f"agents.{py.stem}"
    return None


def get_agent_eval_spec(path: str) -> Optional[dict]:
    """Derive the evaluation agent spec (``module:answer``) for a project.

    The returned spec is directly consumable by ``dva eval run agent`` and by
    the eval framework's ``resolve_agent()``. The project's ``src`` directory
    must be on PYTHONPATH when the eval runs (the eval API handles this).
    """
    module = _find_answer_module(path)
    if not module:
        return None
    return {"spec": f"{module}:answer", "module": module, "src": str(Path(path) / "src")}


def test_agent(path: str, message: str, timeout: int = 120) -> dict:
    """Invoke a generated agent's ``answer()`` entrypoint once and return its reply.

    Runs the agent code in a subprocess using the project's own virtualenv (if
    present), so it exercises the real generated agent without needing a daemon.
    """
    proj = Path(path)
    src = proj / "src"
    agents_dir = src / "agents"
    if not agents_dir.exists():
        return {"ok": False, "error": f"No 'src/agents' directory found in {path}"}

    # Find the agent module exposing a module-level `answer()` entrypoint.
    module = _find_answer_module(path)
    if not module:
        return {
            "ok": False,
            "error": "No agent exposes an answer() entrypoint (expected in src/agents/*.py).",
        }

    # Resolve the Python interpreter: prefer the project's own venv.
    venv_py = proj / ".venv" / "bin" / "python"
    if not venv_py.exists():
        venv_py = proj / ".venv" / "Scripts" / "python.exe"
    python_exe = str(venv_py) if venv_py.exists() else sys.executable

    runner = (
        "import asyncio, json, sys\n"
        f"sys.path.insert(0, {str(src)!r})\n"
        f"from {module} import answer\n"
        "msg = sys.argv[1]\n"
        "try:\n"
        "    out = asyncio.run(answer(msg))\n"
        "    print('__AGENT_RESULT__' + json.dumps({'ok': True, 'response': str(out)}))\n"
        "except Exception as e:\n"
        "    print('__AGENT_RESULT__' + json.dumps({'ok': False, 'error': repr(e)}))\n"
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(src) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

    try:
        result = subprocess.run(
            [python_exe, "-c", runner, message],
            capture_output=True,
            text=True,
            cwd=str(proj),
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Agent test timed out after {timeout}s"}
    except OSError as e:
        return {"ok": False, "error": f"Failed to launch agent: {e}"}

    for line in result.stdout.splitlines():
        if line.startswith("__AGENT_RESULT__"):
            try:
                return json.loads(line[len("__AGENT_RESULT__"):])
            except json.JSONDecodeError:
                break

    tail = (result.stderr or result.stdout or "").strip()[-1000:]
    return {"ok": False, "error": f"Agent did not return a result.\n{tail}"}


def discover_agent_projects(workspace: Optional[Path] = None) -> list[AgentProject]:
    """Discover agent projects using the CLI tracker library."""
    projects = []
    try:
        from agentic_cli.tracker import get_projects
        for row_dict in get_projects():
            tools = row_dict.get("tools") or []
            if isinstance(tools, str):
                tools = json.loads(tools)
            use_case = row_dict.get("use_case")
            projects.append(AgentProject(
                name=row_dict["name"],
                path=row_dict["path"],
                framework=row_dict.get("framework"),
                use_case=use_case,
                tools=tools,
                agent_type=_classify_agent_type(use_case),
                created_at=row_dict.get("created_at"),
            ))
    except Exception:
        pass

    # Also scan workspace for agent projects with src/main.py
    if workspace:
        for child in workspace.iterdir():
            if child.is_dir() and (child / "src" / "main.py").exists():
                # Check if already found via tracker
                if any(p.path == str(child) for p in projects):
                    continue
                # Try to detect use case from pyproject.toml or dva-agent.json
                use_case = _detect_use_case(child)
                projects.append(AgentProject(
                    name=child.name,
                    path=str(child),
                    agent_type=_classify_agent_type(use_case),
                    use_case=use_case,
                ))

    return projects


def _detect_use_case(project_path: Path) -> Optional[str]:
    """Try to detect the use case of an agent project."""
    agent_json = project_path / "dva-agent.json"
    if agent_json.exists():
        try:
            data = json.loads(agent_json.read_text())
            return data.get("use_case")
        except (json.JSONDecodeError, OSError):
            pass

    # Check pyproject.toml for keywords
    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text()
            if "pr-reviewer" in content or "pr_reviewer" in content:
                return "pr-reviewer"
            if "onboard" in content:
                return "onboard"
        except OSError:
            pass

    return None


def validate_project(project_path: str, use_case: Optional[str] = None) -> ProjectValidation:
    """Run file-existence validation checks on a project using CLI library."""
    try:
        from agentic_cli.tracker import validate_project as _cli_validate
        result = _cli_validate(project_path, use_case)
        return ProjectValidation(**result)
    except ImportError:
        # Fallback: minimal check
        p = Path(project_path)
        v = ProjectValidation(
            path_exists=p.exists(),
            has_src=(p / "src").exists(),
            has_pyproject=(p / "pyproject.toml").exists(),
            has_env=(p / ".env").exists(),
        )
        checks = {k: val for k, val in v.model_dump().items() if isinstance(val, bool)}
        v.score = sum(1 for val in checks.values() if val)
        v.total = len(checks)
        return v


def get_project_domain(project_path: str) -> Optional[str]:
    """Read domain name from .domain-context.json if present."""
    ctx = Path(project_path) / ".domain-context.json"
    if ctx.exists():
        try:
            return json.loads(ctx.read_text()).get("domain")
        except (json.JSONDecodeError, OSError):
            pass
    return None
