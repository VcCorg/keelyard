"""Code onboarding service — thin proxy over the agentic-cli `code` commands.

`code onboard` clones/analyzes a repo, installs skills, and optionally builds
KG context — all long-running and full of external logic, so the dashboard
shells out to the real `dva code onboard ...` and streams its output.
"""

import asyncio
import os
import shutil
import sys
from typing import AsyncGenerator, Optional

from pydantic import BaseModel


class OnboardOptions(BaseModel):
    repo: Optional[str] = None          # git URL
    path: Optional[str] = None          # local path
    repo_slug: Optional[str] = None     # slug from domain's linked repos
    domain: Optional[str] = None
    kg: bool = False
    extract_entities: bool = False
    use_domain_skills: bool = False
    link_kg: bool = False
    graphify: bool = False
    agent: bool = False
    code_assist_tool: str = "generic"


def resolve_cli_command() -> list[str]:
    dva = shutil.which("dva")
    if dva:
        return [dva]
    return [sys.executable, "-m", "agentic_cli.main"]


def build_onboard_args(opts: OnboardOptions) -> list[str]:
    args = ["code", "onboard"]
    if opts.repo:
        args += ["--repo", opts.repo]
    if opts.path:
        args += ["--path", opts.path]
    if opts.repo_slug:
        args += ["--repo-slug", opts.repo_slug]
    if opts.domain:
        args += ["--domain", opts.domain]
    args += ["--kg"] if opts.kg else ["--no-kg"]
    if opts.kg:
        args += ["--extract-entities"] if opts.extract_entities else ["--no-extract-entities"]
    args += ["--use-domain-skills"] if opts.use_domain_skills else ["--no-domain-skills"]
    args += ["--link-kg"] if opts.link_kg else ["--no-link-kg"]
    args += ["--graphify"] if opts.graphify else ["--no-graphify"]
    args += ["--agent"] if opts.agent else ["--no-agent"]
    if opts.code_assist_tool:
        args += ["--code-assist-tool", opts.code_assist_tool]
    return args


async def stream_code_command(args: list[str]) -> AsyncGenerator[str, None]:
    """Run `dva code <args>` and yield stdout/stderr lines as they arrive."""
    cmd = resolve_cli_command() + args
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
