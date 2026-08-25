"""Template drift detection for domain meta-repos.

Answers the question the platform could not answer before: *for this live
meta-repo, which files has the template moved on from, which has the team
improved locally, and which are net-new local content worth promoting upstream?*

Three inputs per tracked file:

- ``baseline`` — its sha256 when the meta-repo was generated, from
  ``.platform/template.json`` (see :mod:`template_manifest`).
- ``reference`` — its sha256 in a *fresh* render of the current built-in
  template, using the render inputs recorded at generation time.
- ``live`` — its sha256 on disk right now.

Comparing all three separates a template change from a local edit from a real
conflict, which a two-way diff fundamentally cannot do.

This module is **read-only**. It never writes to the meta-repo; applying updates
(``template upgrade``) and pushing local content upstream (``template promote``)
build on this classification.
"""
from __future__ import annotations

import logging
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional

from .template_manifest import (
    TEMPLATE_VERSION,
    hash_surface,
    read_manifest,
    sha256_file,
)

logger = logging.getLogger(__name__)

# ── Statuses ────────────────────────────────────────────────────────────────

#: On disk matches the current template — nothing to do.
UNCHANGED = "unchanged"
#: Template moved on, local copy untouched — safe to fast-forward.
TEMPLATE_UPDATED = "template-updated"
#: Team edited it, template unchanged — candidate to promote upstream.
LOCALLY_MODIFIED = "locally-modified"
#: Both moved — a real conflict a lead must resolve.
BOTH_MODIFIED = "both-modified"
#: Differs from the template but the generation-time baseline is unknown.
NO_BASELINE = "no-baseline"
#: Net-new local file the template does not generate — promote candidate.
LOCAL_ONLY = "local-only"
#: Template no longer generates it, local copy remains.
TEMPLATE_REMOVED = "template-removed"
#: Template generates it, local copy was deleted — upgrade would restore it.
DELETED = "deleted"

#: Statuses an automated upgrade can apply without human judgement.
UPGRADABLE = frozenset({TEMPLATE_UPDATED, DELETED})
#: Statuses that represent local content worth pushing back to the template.
PROMOTABLE = frozenset({LOCALLY_MODIFIED, LOCAL_ONLY})
#: Statuses that need a human decision.
CONFLICTED = frozenset({BOTH_MODIFIED, NO_BASELINE})

STATUS_ORDER = (
    BOTH_MODIFIED, NO_BASELINE, TEMPLATE_UPDATED, LOCALLY_MODIFIED,
    LOCAL_ONLY, DELETED, TEMPLATE_REMOVED, UNCHANGED,
)


@dataclass
class FileDrift:
    """Classification of one tracked file."""

    path: str
    status: str
    detail: str = ""

    @property
    def upgradable(self) -> bool:
        return self.status in UPGRADABLE

    @property
    def promotable(self) -> bool:
        return self.status in PROMOTABLE

    def to_dict(self) -> dict:
        return {"path": self.path, "status": self.status, "detail": self.detail}


@dataclass
class DriftReport:
    """The full drift picture for one meta-repo."""

    meta_repo: Path
    domain: str
    recorded_version: Optional[str]
    current_version: str = TEMPLATE_VERSION
    has_baseline: bool = False
    entries: list[FileDrift] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        """Per-status counts, in report order, omitting empty statuses."""
        out: dict[str, int] = {}
        for status in STATUS_ORDER:
            n = sum(1 for e in self.entries if e.status == status)
            if n:
                out[status] = n
        return out

    def of_status(self, *statuses: str) -> list[FileDrift]:
        wanted = set(statuses)
        return [e for e in self.entries if e.status in wanted]

    @property
    def upgradable(self) -> list[FileDrift]:
        return [e for e in self.entries if e.upgradable]

    @property
    def promotable(self) -> list[FileDrift]:
        return [e for e in self.entries if e.promotable]

    @property
    def conflicted(self) -> list[FileDrift]:
        return [e for e in self.entries if e.status in CONFLICTED]

    @property
    def drifted(self) -> bool:
        """True when anything differs from a clean render of the template."""
        return any(e.status != UNCHANGED for e in self.entries)

    @property
    def version_behind(self) -> bool:
        """True when the recorded template version isn't the current one."""
        return self.recorded_version is not None and \
            self.recorded_version != self.current_version

    def to_dict(self) -> dict:
        return {
            "meta_repo": str(self.meta_repo),
            "domain": self.domain,
            "recorded_version": self.recorded_version,
            "current_version": self.current_version,
            "has_baseline": self.has_baseline,
            "drifted": self.drifted,
            "version_behind": self.version_behind,
            "counts": self.counts,
            "files": [e.to_dict() for e in self.entries],
        }


# ── Reference render ────────────────────────────────────────────────────────

def render_reference(
    dest_parent: Path,
    domain: str,
    product: str,
    description: str = "",
    owner: str = "",
    repo_name: str = "reference",
) -> Path:
    """Render the current built-in template into ``dest_parent``.

    Everything non-deterministic or environment-dependent is switched off: no
    git (no network/subprocess), no persona generation (AI + domain data), no
    Devin blueprint (reads workspace MCP config). What remains is the pure
    template surface, so any difference from a live repo is real drift.
    """
    from .scaffold import scaffold_domain_meta_repo

    dest_parent.mkdir(parents=True, exist_ok=True)
    scaffold_domain_meta_repo(
        output_dir=dest_parent,
        domain=domain,
        product=product,
        description=description,
        owner=owner,
        git_init=False,
        personas=None,
        persona_context=None,
        enrich_personas=False,
        clone_repos=False,
        write_blueprint=False,
        repo_name=repo_name,
    )
    return dest_parent / repo_name


def render_inputs(meta_repo_path: Path, manifest: Optional[dict], domain: str) -> dict:
    """Resolve the inputs needed to re-render the template.

    Prefers what was recorded at generation time; falls back to the domain's
    own ``domain.yaml`` so meta-repos predating manifests still compare
    meaningfully.
    """
    if manifest:
        recorded = manifest.get("render_inputs") or {}
        if recorded.get("domain"):
            return {
                "domain": str(recorded.get("domain") or domain),
                "product": str(recorded.get("product") or ""),
                "description": str(recorded.get("description") or ""),
                "owner": str(recorded.get("owner") or ""),
            }

    inputs = {"domain": domain, "product": "", "description": "", "owner": ""}
    config = meta_repo_path / ".platform" / "config" / "domain.yaml"
    if config.is_file():
        try:
            import yaml

            data = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
            inputs.update({
                "domain": str(data.get("domain") or domain),
                "product": str(data.get("product") or ""),
                "description": str(data.get("description") or ""),
                "owner": str(data.get("owner") or ""),
            })
        except Exception as e:  # noqa: BLE001 - unreadable config => defaults
            logger.debug("Could not read %s: %s", config, e)
    return inputs


# ── Classification ──────────────────────────────────────────────────────────

def _classify_one(
    rel: str,
    baseline: Optional[str],
    reference: Optional[str],
    live: Optional[str],
    has_baseline: bool,
) -> FileDrift:
    """Classify one file from its three hashes. See module docstring."""
    if live is None:
        if reference is None:
            # Recorded once, gone from both disk and template — nothing to say.
            return FileDrift(rel, TEMPLATE_REMOVED,
                             "removed from the template and deleted locally")
        return FileDrift(rel, DELETED, "generated by the template but missing locally")

    if reference is None:
        if baseline is None:
            return FileDrift(rel, LOCAL_ONLY, "added locally; not part of the template")
        return FileDrift(rel, TEMPLATE_REMOVED,
                         "the template no longer generates this file")

    if live == reference:
        return FileDrift(rel, UNCHANGED, "")

    if baseline is None:
        if not has_baseline:
            return FileDrift(rel, NO_BASELINE,
                             "differs from the template; no generation baseline recorded")
        return FileDrift(rel, NO_BASELINE,
                         "added to the template after this meta-repo was generated")

    if live == baseline:
        return FileDrift(rel, TEMPLATE_UPDATED, "the template has a newer version")
    if reference == baseline:
        return FileDrift(rel, LOCALLY_MODIFIED, "edited locally; the template is unchanged")
    return FileDrift(rel, BOTH_MODIFIED, "edited locally AND updated in the template")


def _build_report(
    meta_repo_path: Path,
    manifest: Optional[dict],
    inputs: dict,
    reference_hashes: dict[str, str],
    live_hashes: dict[str, str],
) -> DriftReport:
    """Assemble a report from the three hash sets."""
    has_baseline = manifest is not None
    baseline_hashes: dict[str, str] = dict((manifest or {}).get("files") or {})
    entries = [
        _classify_one(
            rel,
            baseline_hashes.get(rel),
            reference_hashes.get(rel),
            live_hashes.get(rel),
            has_baseline,
        )
        for rel in sorted(set(baseline_hashes) | set(reference_hashes) | set(live_hashes))
    ]
    return DriftReport(
        meta_repo=meta_repo_path,
        domain=inputs["domain"],
        recorded_version=(manifest or {}).get("template_version"),
        has_baseline=has_baseline,
        entries=entries,
    )


@contextmanager
def reference_context(
    meta_repo_path: Path, domain: str = ""
) -> Iterator[tuple[Path, DriftReport]]:
    """Render the template once and yield ``(reference_root, report)``.

    ``template upgrade`` needs the rendered *files*, not just the hashes, to copy
    updates from — and rendering twice would be both slow and racy. The render
    lives only for the duration of the block.

    Raises ``FileNotFoundError`` if the path isn't a meta-repo.
    """
    meta_repo_path = Path(meta_repo_path)
    if not (meta_repo_path / ".platform" / "config").is_dir():
        raise FileNotFoundError(
            f"Not a domain meta-repo (no .platform/config): {meta_repo_path}")

    manifest = read_manifest(meta_repo_path)
    domain = domain or render_inputs(meta_repo_path, manifest, "")["domain"]
    inputs = render_inputs(meta_repo_path, manifest, domain)

    with tempfile.TemporaryDirectory(prefix="keel-template-ref-") as tmp:
        reference_root = render_reference(Path(tmp), **inputs)
        report = _build_report(
            meta_repo_path, manifest, inputs,
            hash_surface(reference_root), hash_surface(meta_repo_path),
        )
        yield reference_root, report


def classify(meta_repo_path: Path, domain: str = "") -> DriftReport:
    """Classify every tracked file in a meta-repo against the current template.

    Read-only. Raises ``FileNotFoundError`` if the path isn't a meta-repo.
    """
    with reference_context(meta_repo_path, domain=domain) as (_, report):
        return report


def classify_domain(domain: str) -> DriftReport:
    """Classify a domain's meta-repo, resolved by the standard conventions."""
    from .detector import detect_domain_meta_repo

    meta = detect_domain_meta_repo(domain)
    if meta is None:
        raise FileNotFoundError(
            f"No meta-repo found for domain '{domain}'. Create one with "
            f"'keel domain init {domain}'.")
    return classify(meta, domain=domain)


__all__ = [
    "UNCHANGED", "TEMPLATE_UPDATED", "LOCALLY_MODIFIED", "BOTH_MODIFIED",
    "NO_BASELINE", "LOCAL_ONLY", "TEMPLATE_REMOVED", "DELETED",
    "UPGRADABLE", "PROMOTABLE", "CONFLICTED", "STATUS_ORDER",
    "FileDrift", "DriftReport", "classify", "classify_domain",
    "render_reference", "reference_context", "render_inputs", "sha256_file",
]
