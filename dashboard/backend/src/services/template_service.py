"""Template lifecycle for the dashboard — drift, upgrade, promote.

Surfaces the two-way template flow that `keel domain template` implements, so a
tech lead can see and act on it from Governance → Workspaces instead of dropping
to a terminal:

- **status**   — how has this domain meta-repo diverged from the template? (read)
- **upgrade**  — pull safe template updates down into the repo.        (writes)
- **promote**  — push a local improvement up into the shared template. (writes)

Reads import the CLI library directly. Writes shell out to the real CLI and
stream stdout, so the git safety net, dry-run defaults and confirmation
semantics live in exactly one place and the dashboard can never diverge from
what the command line does.

Note that a status check *renders the whole template* into a temp dir to compare
against, which takes a second or two. It is therefore never folded into the hot
path of resolving a workspace target — the UI asks for it explicitly.
"""

from typing import AsyncGenerator, Optional

from pydantic import BaseModel


# ── Models ───────────────────────────────────────────────────────────────────

class TemplateFile(BaseModel):
    path: str
    status: str
    detail: str = ""


class TemplateDriftSummary(BaseModel):
    """Counts only — cheap enough to render a chip from."""

    domain: str
    meta_repo: Optional[str] = None
    template_version: str = ""
    recorded_version: Optional[str] = None
    has_baseline: bool = False
    version_behind: bool = False
    drifted: bool = False
    counts: dict[str, int] = {}
    upgradable: int = 0
    promotable: int = 0
    conflicted: int = 0
    error: Optional[str] = None   # set when the check could not run


class TemplateStatus(TemplateDriftSummary):
    files: list[TemplateFile] = []


class OverlayInfo(BaseModel):
    overlay_root: str
    files: list[str] = []
    env_var: str = ""


class PromotableFiles(BaseModel):
    domain: str
    meta_repo: Optional[str] = None
    overlay_root: str = ""
    files: list[TemplateFile] = []


# ── Reads ────────────────────────────────────────────────────────────────────

def _classify(domain: str, meta: Optional[str] = None):
    from pathlib import Path

    from agentic_cli.meta_repo import template_drift as drift

    if meta:
        return drift.classify(Path(meta).expanduser(), domain=domain)
    return drift.classify_domain(domain)


def template_status(domain: str, meta: Optional[str] = None) -> TemplateStatus:
    """Full drift classification for a domain meta-repo.

    Raises FileNotFoundError when the domain has no meta-repo, which the API
    maps to 404 — the domain simply hasn't been scaffolded yet.
    """
    report = _classify(domain, meta)
    return TemplateStatus(
        domain=report.domain,
        meta_repo=str(report.meta_repo),
        template_version=report.current_version,
        recorded_version=report.recorded_version,
        has_baseline=report.has_baseline,
        version_behind=report.version_behind,
        drifted=report.drifted,
        counts=report.counts,
        upgradable=len(report.upgradable),
        promotable=len(report.promotable),
        conflicted=len(report.conflicted),
        files=[TemplateFile(path=e.path, status=e.status, detail=e.detail)
               for e in report.entries],
    )


def drift_summary(domain: str) -> TemplateDriftSummary:
    """Counts-only drift, never raising.

    Used to decorate a workspace target, where a template problem must not break
    the page: any failure is reported in ``error`` and the caller still renders.
    """
    try:
        full = template_status(domain)
    except FileNotFoundError as e:
        return TemplateDriftSummary(domain=domain, error=str(e))
    except Exception as e:  # noqa: BLE001
        return TemplateDriftSummary(domain=domain, error=f"{type(e).__name__}: {e}")
    return TemplateDriftSummary(**full.model_dump(exclude={"files"}))


def overlay_info() -> OverlayInfo:
    """What the shared template overlay currently provides."""
    from agentic_cli.meta_repo import template_overlay as ov

    root = ov.overlay_root()
    return OverlayInfo(overlay_root=str(root), files=ov.list_overlay(root),
                       env_var=ov.OVERLAY_ENV)


def promotable_files(domain: str) -> PromotableFiles:
    """Files this domain could contribute back to the template."""
    from pathlib import Path

    from agentic_cli.meta_repo import template_overlay as ov
    from agentic_cli.meta_repo import template_promote as prom
    from agentic_cli.meta_repo.detector import detect_domain_meta_repo

    meta: Optional[Path] = detect_domain_meta_repo(domain)
    if meta is None:
        raise FileNotFoundError(f"No meta-repo found for domain '{domain}'")

    entries, inputs = prom.promotable(meta, domain=domain)
    return PromotableFiles(
        domain=inputs.get("domain") or domain,
        meta_repo=str(meta),
        overlay_root=str(ov.overlay_root()),
        files=[TemplateFile(path=e.path, status=e.status, detail=e.detail)
               for e in entries],
    )


# ── Writes (streamed through the real CLI) ───────────────────────────────────

def stream_upgrade(domain: str, apply: bool = False, prune: bool = False,
                   force: bool = False) -> AsyncGenerator[str, None]:
    """Stream ``keel domain template upgrade``.

    ``apply=False`` (the CLI default) previews without touching the repo. The
    CLI's own git guard refuses to overwrite files with uncommitted changes
    unless ``force`` — that check is deliberately not duplicated here.
    """
    from src.services.workspace_service import _stream_cli

    args = ["domain", "template", "upgrade", domain, "--json"]
    if apply:
        # -y: the CLI prompts for confirmation interactively; there is no TTY
        # here, and the dashboard already confirmed with the user.
        args += ["--apply", "-y"]
    if prune:
        args.append("--prune")
    if force:
        args.append("--force")
    return _stream_cli(args)


def stream_promote(domain: str, files: list[str], apply: bool = False,
                   push: bool = False, allow_unreviewed: bool = False,
                   ) -> AsyncGenerator[str, None]:
    """Stream ``keel domain template promote``.

    Publishing stays opt-in (``push``): the overlay is shared by every domain,
    so a promotion normally stops at a committed branch for review.
    """
    from src.services.workspace_service import _stream_cli

    args = ["domain", "template", "promote", domain, "--json"]
    for f in files:
        args += ["--file", f]
    if apply:
        args.append("--apply")
    if push:
        args.append("--push")
    if allow_unreviewed:
        args.append("--allow-unreviewed")
    return _stream_cli(args)
