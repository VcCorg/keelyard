"""Push a domain's local template improvements back up to the shared template.

The last missing leg. A tech lead sharpens their domain's ``AGENTS.md`` or adds
a ``docs/`` playbook; without this it stays in that one repo forever and every
future scaffold starts from the older text.

This is the mirror of :mod:`template_upgrade`:

- ``upgrade`` takes ``UPGRADABLE`` drift (template ahead) and pulls it **down**.
- ``promote`` takes ``PROMOTABLE`` drift (local ahead) and pushes it **up** into
  the overlay, from where every other domain's next ``upgrade`` fast-forwards it.

Publishing is deliberately a reviewed, opt-in step: the overlay is shared by
every domain, so a promotion stages a branch in the platform repo and hands the
push command to a human. Tokenization is heuristic, so a promotion also refuses
to proceed silently when it cannot verify its own round-trip.

One subtlety: after promoting, the file the domain contributed *is* the template.
The source repo's own baseline is therefore advanced to match (see
:func:`_rebaseline_source`), otherwise the promoting domain would keep reporting
its own contribution as drift forever and could never promote a later revision.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import template_drift as drift
from . import template_overlay as ov
from .template_overlay import PromotionError

logger = logging.getLogger(__name__)


@dataclass
class PromotionResult:
    """Outcome of promoting one or more files into the template overlay."""

    domain: str
    meta_repo: Path
    overlay_root: Path
    plans: list[ov.PromotionPlan] = field(default_factory=list)
    written: list[str] = field(default_factory=list)
    rebaselined: list[str] = field(default_factory=list)
    dry_run: bool = False
    branch: str = ""
    commit: str = ""
    committed: bool = False
    pushed: bool = False
    push_hint: str = ""
    review_required: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "domain": self.domain, "meta_repo": str(self.meta_repo),
            "overlay_root": str(self.overlay_root),
            "plans": [p.to_dict() for p in self.plans],
            "written": self.written, "rebaselined": self.rebaselined,
            "dry_run": self.dry_run,
            "branch": self.branch, "commit": self.commit,
            "committed": self.committed, "pushed": self.pushed,
            "push_hint": self.push_hint,
            "review_required": self.review_required,
        }


# ── Discovery ───────────────────────────────────────────────────────────────

def promotable(meta_repo_path: Path, domain: str = "") -> tuple[list[drift.FileDrift], dict]:
    """Local files that are ahead of the template, plus the render inputs.

    ``PROMOTABLE`` is ``locally-modified`` (an improved template file) and
    ``local-only`` (a file this domain added). Conflicted files are excluded:
    when both sides moved, the template's own change must be reconciled first.
    """
    from .template_manifest import read_manifest

    report = drift.classify(meta_repo_path, domain=domain)
    manifest = read_manifest(meta_repo_path)
    inputs = drift.render_inputs(meta_repo_path, manifest, report.domain)
    return list(report.promotable), inputs


# ── Git (platform repo hosting the overlay) ─────────────────────────────────

def repo_root_of(path: Path) -> Optional[Path]:
    """The git repo containing ``path``, or None when it isn't in one."""
    for candidate in [Path(path), *Path(path).parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True)


def branch_name(domain: str, rels: list[str]) -> str:
    """``template-promote/<domain>/<file-or-count>``."""
    def clean(s: str) -> str:
        return re.sub(r"[^A-Za-z0-9._-]+", "-", s).strip("-.")

    leaf = (clean(rels[0].replace("/", "-")) if len(rels) == 1
            else f"{len(rels)}-files")
    parts = [clean(domain), leaf]
    return "/".join(["template-promote", *[p for p in parts if p]])


# ── Promote ─────────────────────────────────────────────────────────────────

def promote(
    meta_repo_path: Path,
    paths: list[str],
    domain: str = "",
    *,
    dry_run: bool = False,
    commit: bool = True,
    push: bool = False,
    allow_unreviewed: bool = False,
    overlay: Optional[Path] = None,
) -> PromotionResult:
    """Promote local files into the template overlay.

    Args:
        meta_repo_path: The domain meta-repo the content comes from.
        paths: Repo-relative files to promote.
        domain: Domain slug (inferred when omitted).
        dry_run: Plan and validate only; write nothing.
        commit: Create a branch + commit in the platform repo.
        push: Also push that branch (opt-in — the overlay is shared).
        allow_unreviewed: Proceed even when a plan flags residual
            domain-specific content. Without this, such files are refused.
        overlay: Override the overlay directory (tests / org-hosted overlays).

    Returns:
        A :class:`PromotionResult`.

    Raises:
        PromotionError: If nothing is promotable, a path is ineligible, or
            tokenization cannot be verified.
    """
    meta_repo_path = Path(meta_repo_path)
    entries, inputs = promotable(meta_repo_path, domain=domain)
    by_path = {e.path: e for e in entries}
    resolved_domain = inputs.get("domain", "") or domain
    root = Path(overlay) if overlay is not None else ov.overlay_root()

    if not paths:
        raise PromotionError("No files given to promote")

    plans: list[ov.PromotionPlan] = []
    for rel in paths:
        entry = by_path.get(rel)
        if entry is None:
            raise PromotionError(
                f"'{rel}' is not promotable — only locally-modified or "
                f"local-only files can be promoted (see 'template status')")
        plan = ov.plan_promotion(meta_repo_path, rel, entry.status, inputs, root=root)

        # A template that doesn't render back to the file it came from is broken.
        original = (meta_repo_path / rel).read_text(encoding="utf-8")
        if not ov.verify_round_trip(plan, inputs, original):
            raise PromotionError(
                f"Tokenizing '{rel}' does not round-trip back to the original "
                f"file — refusing to publish a template that would generate "
                f"different content")
        plans.append(plan)

    review = [p.path for p in plans if p.residuals]
    if review and not allow_unreviewed:
        detail = "; ".join(
            f"{p.path}: " + ", ".join(f"{r.count}× {r.kind} ({r.sample})"
                                      for r in p.residuals[:3])
            for p in plans if p.residuals)
        raise PromotionError(
            f"Content still looks domain-specific and would leak into every "
            f"domain: {detail}. Clean it up, or rerun with --allow-unreviewed "
            f"if these are intentional.")

    result = PromotionResult(
        domain=resolved_domain, meta_repo=meta_repo_path, overlay_root=root,
        plans=plans, dry_run=dry_run,
        review_required=[p.path for p in plans if p.needs_review],
    )
    if dry_run:
        return result

    for plan in plans:
        ov.write_promotion(plan)
        result.written.append(plan.path)

    _rebaseline_source(result)
    _stage(result, commit=commit, push=push)
    _audit(result)
    return result


def _rebaseline_source(result: PromotionResult) -> None:
    """Record the promoted files as the source repo's new template baseline.

    The round-trip check already proved the overlay regenerates these files
    byte-for-byte, so the domain is now genuinely in sync with the template.
    Without this the promoting repo would report its own contribution as
    ``local-only``/``no-baseline`` forever — permanently "drifted", and blocked
    from promoting a later revision of the same file (only PROMOTABLE drift is
    eligible, and conflicted drift is not).

    Only the promoted paths are touched; every other baseline entry is left
    exactly as it was.
    """
    from .template_manifest import (
        MANIFEST_REL, TEMPLATE_VERSION, read_manifest, sha256_file,
    )

    manifest = read_manifest(result.meta_repo)
    if manifest is None:
        # No baseline was ever recorded (pre-versioning repo). Writing a partial
        # manifest here would misrepresent every other file as untracked, so
        # leave it to `template upgrade`, which rebaselines the whole surface.
        return

    files = dict(manifest.get("files") or {})
    for rel in result.written:
        src = result.meta_repo / rel
        if src.is_file():
            files[rel] = sha256_file(src)
            result.rebaselined.append(rel)
    if not result.rebaselined:
        return

    manifest["files"] = dict(sorted(files.items()))
    manifest["promoted_at"] = datetime.now(timezone.utc).isoformat()
    manifest.setdefault("template_version", TEMPLATE_VERSION)
    target = result.meta_repo / MANIFEST_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _stage(result: PromotionResult, *, commit: bool, push: bool) -> None:
    """Branch + commit the overlay change in the platform repo."""
    repo = repo_root_of(result.overlay_root)
    if repo is None:
        result.push_hint = (
            f"{result.overlay_root} is not inside a git repository — commit the "
            f"overlay change however that directory is managed")
        return
    if not commit:
        result.push_hint = f"git -C {repo} status  # review, then commit"
        return

    branch = branch_name(result.domain, result.written)
    result.branch = branch
    if _git(repo, "rev-parse", "--verify", branch).returncode == 0:
        _git(repo, "checkout", branch)
    else:
        _git(repo, "checkout", "-b", branch)

    rels = [str((result.overlay_root / p).relative_to(repo)) for p in result.written]
    _git(repo, "add", *rels)
    files = ", ".join(result.written)
    message = (
        f"template: promote {files} from {result.domain}\n\n"
        f"Promoted from the {result.domain} meta-repo into the shared template "
        f"overlay, so future scaffolds and 'domain template upgrade' pick it up."
    )
    res = _git(repo, "commit", "-m", message)
    if res.returncode == 0:
        result.committed = True
        result.commit = _git(repo, "rev-parse", "--short", "HEAD").stdout.strip()
    else:
        logger.debug("commit produced no change: %s", res.stdout or res.stderr)

    if push:
        pushed = _git(repo, "push", "-u", "origin", branch)
        result.pushed = pushed.returncode == 0
        if not result.pushed:
            result.push_hint = (
                f"push failed ({(pushed.stderr or '').strip()[:160]}); retry: "
                f"git -C {repo} push -u origin {branch}")
    if not result.pushed and not result.push_hint:
        result.push_hint = f"git -C {repo} push -u origin {branch}"


def _audit(result: PromotionResult) -> None:
    try:
        from agentic_cli.tracker import record_activity

        record_activity(
            command="domain", subcommand="template-promote",
            entity_type="domain", entity_id=result.domain,
            args={"domain": result.domain, "files": result.written},
            details={"branch": result.branch, "committed": result.committed,
                     "pushed": result.pushed},
        )
    except Exception:  # noqa: BLE001
        pass


def promote_domain(domain: str, paths: list[str], **kwargs) -> PromotionResult:
    """Promote from a domain's meta-repo, resolved by the standard conventions."""
    from .detector import detect_domain_meta_repo

    meta = detect_domain_meta_repo(domain)
    if meta is None:
        raise FileNotFoundError(
            f"No meta-repo found for domain '{domain}'. Create one with "
            f"'keel domain init {domain}'.")
    return promote(meta, paths, domain=domain, **kwargs)


__all__ = [
    "PromotionResult", "PromotionError", "promotable", "promote",
    "promote_domain", "branch_name", "repo_root_of",
]
