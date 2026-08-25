"""Apply template updates to an existing domain meta-repo.

Phase 1 could only *report* drift. This applies the safe part of it, so a
template improvement reaches meta-repos that were generated months ago instead
of only new ones.

What it does, and deliberately does not, touch:

===================  ==========================================================
``template-updated`` **fast-forwarded** — local copy is untouched since
                     generation, so taking the template's version loses nothing.
``deleted``          **restored** from the template.
``both-modified``    **left alone**, with the template's version written beside
``no-baseline``      it as ``<file>.new`` for a human to merge.
``locally-modified`` **left alone** — this is the domain's own work, and the
``local-only``       path for it is upstream promotion, not being overwritten.
``template-removed`` **left alone** unless ``--prune``: silently deleting a
                     team's file is never the safe default.
===================  ==========================================================

Two safety properties worth stating explicitly:

- **No 3-way merge is attempted.** The manifest stores content *hashes*, not
  content, so the generation-time baseline cannot be reconstructed and a true
  3-way merge is impossible. Pretending otherwise would silently mangle files;
  conflicts get a ``.new`` sidecar and stay conflicts until a human resolves
  them.
- **Re-baselining is selective.** Rewriting the whole manifest from disk after
  an upgrade would record a locally-modified file's *edited* hash as its
  baseline — which the classifier would then read as ``template-updated`` and
  happily overwrite on the next upgrade, destroying the local edit. So a file's
  baseline is only advanced when its content actually matches the template.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import template_drift as drift
from .template_manifest import (
    MANIFEST_REL,
    TEMPLATE_VERSION,
    hash_surface,
    read_manifest,
)

logger = logging.getLogger(__name__)

# Actions recorded per file.
UPDATED = "updated"            #: Fast-forwarded to the template's version.
RESTORED = "restored"          #: Re-created after being deleted locally.
CONFLICT = "conflict"          #: Left alone; ``.new`` sidecar written.
PRUNED = "pruned"              #: Removed because the template dropped it.
SKIPPED = "skipped"            #: Intentionally untouched (with a reason).


@dataclass
class FileAction:
    """What the upgrade did (or would do) to one file."""

    path: str
    action: str
    status: str                 # the drift status that drove the decision
    detail: str = ""
    sidecar: str = ""           # relative path of a written .new file

    def to_dict(self) -> dict:
        return {"path": self.path, "action": self.action, "status": self.status,
                "detail": self.detail, "sidecar": self.sidecar}


@dataclass
class UpgradeReport:
    """Outcome of an upgrade (or a dry run)."""

    meta_repo: Path
    domain: str
    from_version: Optional[str]
    to_version: str = TEMPLATE_VERSION
    dry_run: bool = False
    actions: list[FileAction] = field(default_factory=list)
    manifest_written: bool = False
    blocked: list[str] = field(default_factory=list)

    def of_action(self, *actions: str) -> list[FileAction]:
        wanted = set(actions)
        return [a for a in self.actions if a.action in wanted]

    @property
    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for a in self.actions:
            out[a.action] = out.get(a.action, 0) + 1
        return out

    @property
    def changed(self) -> int:
        """Files an upgrade would write or delete."""
        return len(self.of_action(UPDATED, RESTORED, PRUNED))

    @property
    def conflicts(self) -> list[FileAction]:
        return self.of_action(CONFLICT)

    def to_dict(self) -> dict:
        return {
            "meta_repo": str(self.meta_repo), "domain": self.domain,
            "from_version": self.from_version, "to_version": self.to_version,
            "dry_run": self.dry_run, "counts": self.counts,
            "changed": self.changed, "manifest_written": self.manifest_written,
            "blocked": self.blocked,
            "actions": [a.to_dict() for a in self.actions],
        }


# ── Git safety net ──────────────────────────────────────────────────────────

def uncommitted_paths(meta_repo: Path, rels: list[str]) -> set[str]:
    """Which of ``rels`` have uncommitted changes in git.

    Overwriting a tracked-but-unmodified file is recoverable (``git checkout``);
    overwriting uncommitted work is not. Those files are skipped unless forced.
    Returns an empty set when git isn't available, which the caller surfaces as
    "no safety net" rather than pretending it checked.
    """
    if not rels or not (Path(meta_repo) / ".git").exists():
        return set()
    try:
        res = subprocess.run(
            ["git", "-C", str(meta_repo), "status", "--porcelain", "--", *rels],
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.SubprocessError, OSError) as e:
        logger.debug("git status failed: %s", e)
        return set()
    if res.returncode != 0:
        return set()

    dirty: set[str] = set()
    for line in res.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip().strip('"')
        # Renames are reported as "old -> new"; the new path is what matters.
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        dirty.add(path)
    return dirty


# ── Manifest re-baselining ──────────────────────────────────────────────────

def _rebaseline(
    meta_repo: Path,
    old_manifest: Optional[dict],
    reference_hashes: dict[str, str],
    inputs: dict,
) -> dict:
    """Build the post-upgrade manifest.

    A file's baseline advances to the template's hash **only** when the file on
    disk now matches the template. Otherwise its previous baseline is preserved
    (see the module docstring for why blanket re-baselining is unsafe).
    """
    old_files: dict[str, str] = dict((old_manifest or {}).get("files") or {})
    live = hash_surface(meta_repo)

    files: dict[str, str] = {}
    for rel, ref_hash in reference_hashes.items():
        if live.get(rel) == ref_hash:
            files[rel] = ref_hash          # in sync — the template IS the baseline
        elif rel in old_files:
            files[rel] = old_files[rel]    # local divergence — keep the old baseline
    # Files the template no longer generates keep their baseline so they stay
    # classifiable as `template-removed` rather than becoming `local-only`.
    for rel, old_hash in old_files.items():
        files.setdefault(rel, old_hash)

    manifest = {
        "template_version": TEMPLATE_VERSION,
        "generated_at": (old_manifest or {}).get("generated_at")
                        or datetime.now(timezone.utc).isoformat(),
        "upgraded_at": datetime.now(timezone.utc).isoformat(),
        "render_inputs": {
            "domain": inputs.get("domain", ""),
            "product": inputs.get("product", ""),
            "description": inputs.get("description", ""),
            "owner": inputs.get("owner", ""),
        },
        "files": dict(sorted(files.items())),
    }
    if old_manifest and old_manifest.get("template_version"):
        manifest["upgraded_from"] = old_manifest["template_version"]
    return manifest


# ── Upgrade ─────────────────────────────────────────────────────────────────

def upgrade(
    meta_repo_path: Path,
    domain: str = "",
    *,
    dry_run: bool = False,
    prune: bool = False,
    write_conflicts: bool = True,
    force: bool = False,
) -> UpgradeReport:
    """Apply safe template updates to a meta-repo.

    Args:
        meta_repo_path: The meta-repo to upgrade.
        domain: Domain slug (inferred from the repo when omitted).
        dry_run: Classify and decide, but write nothing.
        prune: Also delete files the template no longer generates.
        write_conflicts: Write ``<file>.new`` beside conflicted files.
        force: Overwrite files with uncommitted git changes.

    Returns:
        An :class:`UpgradeReport`. Raises ``FileNotFoundError`` if the path is
        not a meta-repo.
    """
    meta_repo_path = Path(meta_repo_path)
    old_manifest = read_manifest(meta_repo_path)

    with drift.reference_context(meta_repo_path, domain=domain) as (ref_root, report):
        actions: list[FileAction] = []
        blocked: list[str] = []

        # Guard: never clobber uncommitted work unless explicitly forced.
        write_targets = [e.path for e in report.entries
                         if e.status in (drift.TEMPLATE_UPDATED,)]
        dirty = set() if force else uncommitted_paths(meta_repo_path, write_targets)
        if not (meta_repo_path / ".git").exists():
            blocked.append(
                "not a git repository — overwrites cannot be undone with git")

        for entry in report.entries:
            rel, status = entry.path, entry.status
            live = meta_repo_path / rel
            reference = ref_root / rel

            if status == drift.UNCHANGED:
                continue

            if status == drift.TEMPLATE_UPDATED:
                if rel in dirty:
                    actions.append(FileAction(
                        rel, SKIPPED, status,
                        "has uncommitted changes — rerun with --force to overwrite"))
                    continue
                if not dry_run:
                    live.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(reference, live)
                actions.append(FileAction(rel, UPDATED, status,
                                          "fast-forwarded to the template version"))

            elif status == drift.DELETED:
                if not dry_run:
                    live.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(reference, live)
                actions.append(FileAction(rel, RESTORED, status,
                                          "restored from the template"))

            elif status in drift.CONFLICTED:
                sidecar = ""
                if write_conflicts and reference.is_file():
                    sidecar = f"{rel}.new"
                    if not dry_run:
                        target = meta_repo_path / sidecar
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(reference, target)
                actions.append(FileAction(
                    rel, CONFLICT, status,
                    "left as-is; compare with the .new sidecar and merge by hand"
                    if sidecar else "left as-is; template version unavailable",
                    sidecar=sidecar))

            elif status == drift.TEMPLATE_REMOVED:
                if prune:
                    if not dry_run and live.is_file():
                        live.unlink()
                    actions.append(FileAction(rel, PRUNED, status,
                                              "removed (no longer in the template)"))
                else:
                    actions.append(FileAction(
                        rel, SKIPPED, status,
                        "no longer in the template — rerun with --prune to remove"))

            else:  # locally-modified / local-only — the domain's own work
                actions.append(FileAction(
                    rel, SKIPPED, status,
                    "local content preserved; promote it upstream instead"))

        result = UpgradeReport(
            meta_repo=meta_repo_path, domain=report.domain,
            from_version=report.recorded_version, dry_run=dry_run,
            actions=actions, blocked=blocked,
        )

        # Re-baseline only after files have actually been written, so the new
        # manifest reflects the real on-disk state.
        if not dry_run:
            inputs = drift.render_inputs(meta_repo_path, old_manifest, report.domain)
            manifest = _rebaseline(
                meta_repo_path, old_manifest, hash_surface(ref_root), inputs)
            target = meta_repo_path / MANIFEST_REL
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            result.manifest_written = True

    _audit(result)
    return result


def upgrade_domain(domain: str, **kwargs) -> UpgradeReport:
    """Upgrade a domain's meta-repo, resolved by the standard conventions."""
    from .detector import detect_domain_meta_repo

    meta = detect_domain_meta_repo(domain)
    if meta is None:
        raise FileNotFoundError(
            f"No meta-repo found for domain '{domain}'. Create one with "
            f"'keel domain init {domain}'.")
    return upgrade(meta, domain=domain, **kwargs)


def _audit(result: UpgradeReport) -> None:
    """Record the upgrade centrally (never fatal)."""
    try:
        from agentic_cli.tracker import record_activity

        record_activity(
            command="domain", subcommand="template-upgrade",
            entity_type="domain", entity_id=result.domain,
            args={"domain": result.domain, "dry_run": result.dry_run},
            details={"from_version": result.from_version,
                     "to_version": result.to_version,
                     "counts": result.counts,
                     "changed": result.changed},
        )
    except Exception:  # noqa: BLE001 - auditing must never break an upgrade
        pass


__all__ = [
    "UPDATED", "RESTORED", "CONFLICT", "PRUNED", "SKIPPED",
    "FileAction", "UpgradeReport", "upgrade", "upgrade_domain",
    "uncommitted_paths",
]
