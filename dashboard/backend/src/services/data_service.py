"""Data source service — thin proxy over the agentic-cli `data` commands.

Reads import the CLI's config loader directly (single source of truth for the
`~/.agent-cli-agentic/config.json` layout). Mutations (create/delete) shell out
to the real `dva data ...` CLI so all validation lives in exactly one place.
"""

import os
import shutil
import subprocess
import sys
from typing import Optional

from pydantic import BaseModel


class DataSourceInfo(BaseModel):
    name: str
    type: str
    location: str
    description: str = ""
    project: str = ""
    tags: list[str] = []
    kg_status: str = ""
    confluence_space: Optional[str] = None
    git_branch: Optional[str] = None
    git_tag: Optional[str] = None
    created_at: Optional[str] = None


class CommandResult(BaseModel):
    success: bool
    output: str


def _load_config() -> dict:
    from agentic_cli.commands.data import load_config
    return load_config() or {}


def resolve_cli_command() -> list[str]:
    dva = shutil.which("dva")
    if dva:
        return [dva]
    return [sys.executable, "-m", "agentic_cli.main"]


def list_data_sources() -> list[DataSourceInfo]:
    config = _load_config()
    sources = (config.get("data") or {}).get("sources") or []
    out: list[DataSourceInfo] = []
    for s in sources:
        git = s.get("git") or {}
        out.append(DataSourceInfo(
            name=s.get("name", ""),
            type=s.get("type", ""),
            location=s.get("location", ""),
            description=s.get("description", "") or "",
            project=s.get("project", "") or "",
            tags=s.get("tags") or [],
            kg_status=s.get("kg_status", "") or "",
            confluence_space=s.get("confluence_space"),
            git_branch=git.get("branch"),
            git_tag=git.get("tag"),
            created_at=s.get("created_at"),
        ))
    return out


def _run_cli(args: list[str]) -> CommandResult:
    cmd = resolve_cli_command() + args
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    return CommandResult(success=proc.returncode == 0, output=output.strip())


class ValidationResult(BaseModel):
    valid: bool
    message: str
    level: str  # "ok" | "warning" | "error"


def validate_location(source_type: str, location: str) -> ValidationResult:
    """Validate a source location using the CLI's own validator (single source of truth)."""
    if not location.strip():
        return ValidationResult(valid=False, message="Location is required.", level="error")
    try:
        from agentic_cli.commands.data import validate_source_location
        ok, message = validate_source_location(source_type, location)
    except Exception as e:
        return ValidationResult(valid=False, message=str(e), level="error")
    if not ok:
        return ValidationResult(valid=False, message=message, level="error")
    level = "warning" if "Warning" in message else "ok"
    return ValidationResult(valid=True, message=message, level=level)


def create_data_source(
    name: str,
    source_type: str,
    source_location: str,
    description: str = "",
    tags: Optional[list[str]] = None,
    project: str = "",
    confluence_space: str = "",
    git_branch: str = "",
    git_tag: str = "",
) -> CommandResult:
    """Create a data source by shelling out to `dva data create` (reuses validation)."""
    args = [
        "data", "create",
        "--name", name,
        "--source-type", source_type,
        "--source-location", source_location,
    ]
    if description:
        args += ["--description", description]
    if tags:
        args += ["--tags", ",".join(tags)]
    if project:
        args += ["--project", project]
    if confluence_space:
        args += ["--confluence-space", confluence_space]
    if git_branch:
        args += ["--git-branch", git_branch]
    if git_tag:
        args += ["--git-tag", git_tag]
    return _run_cli(args)


def delete_data_source(name: str) -> CommandResult:
    return _run_cli(["data", "delete", name, "--yes"])
