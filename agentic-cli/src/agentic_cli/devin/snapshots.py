"""Per-domain Devin snapshot registry + meta-repo drift verification.

Snapshot ids are built from a domain meta-repo's ``.devin/environment.yaml``
blueprint (see :mod:`agentic_cli.devin.blueprint`) and stored per-domain in the
shared CLI config by :class:`agentic_cli.devin.config.DevinConfig`.

This module surfaces that registry and adds *provenance verification*: when a
snapshot is built we record the meta-repo git SHA and a hash of the blueprint
file, so we can later detect whether the meta-repo has drifted from the state a
snapshot was built from (i.e. the snapshot is stale and should be rebuilt).
"""
from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from agentic_cli.devin.blueprint import BLUEPRINT_DIR, ENVIRONMENT_FILE
from agentic_cli.devin.config import DevinConfig

# Verification states.
STATE_OK = "ok"                     # snapshot matches current meta-repo state
STATE_DRIFT = "drift"               # meta-repo changed since the snapshot was built
STATE_NO_SNAPSHOT = "no-snapshot"   # domain configured but no snapshot built yet
STATE_META_MISSING = "meta-missing" # meta-repo path / blueprint file not found
STATE_UNVERIFIABLE = "unverifiable" # snapshot registered without provenance to check


def git_head_sha(repo_path: Path) -> Optional[str]:
    """Return the short HEAD SHA of ``repo_path``, or ``None`` if not a repo."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return (proc.stdout or "").strip() or None


def blueprint_path_for(meta_repo_path: Path) -> Path:
    """Path to the DRS blueprint inside a meta-repo."""
    return meta_repo_path / BLUEPRINT_DIR / ENVIRONMENT_FILE


def blueprint_hash(blueprint_file: Path) -> Optional[str]:
    """Return ``sha256:<hex12>`` of a blueprint file, or ``None`` if absent."""
    try:
        data = blueprint_file.read_bytes()
    except OSError:
        return None
    return "sha256:" + hashlib.sha256(data).hexdigest()[:12]


def capture_provenance(meta_repo_path: Path) -> dict[str, Any]:
    """Snapshot the current meta-repo state for later drift detection.

    Returns a dict of ``meta_repo_path`` (absolute), ``meta_repo_sha``,
    ``blueprint_hash`` and ``built_at`` (UTC ISO). Fields that cannot be
    determined are omitted so they don't overwrite existing values.
    """
    prov: dict[str, Any] = {
        "meta_repo_path": str(meta_repo_path.resolve()),
        "built_at": datetime.now(timezone.utc).isoformat(),
    }
    sha = git_head_sha(meta_repo_path)
    if sha:
        prov["meta_repo_sha"] = sha
    bph = blueprint_hash(blueprint_path_for(meta_repo_path))
    if bph:
        prov["blueprint_hash"] = bph
    return prov


@dataclass
class SnapshotStatus:
    domain: str
    snapshot_id: Optional[str] = None
    blueprint_id: Optional[str] = None
    knowledge_folder: Optional[str] = None
    built_at: Optional[str] = None
    meta_repo_path: Optional[str] = None
    recorded_sha: Optional[str] = None
    current_sha: Optional[str] = None
    recorded_blueprint_hash: Optional[str] = None
    current_blueprint_hash: Optional[str] = None
    state: str = STATE_NO_SNAPSHOT
    detail: str = ""

    @property
    def stale(self) -> bool:
        return self.state == STATE_DRIFT


def _verify_record(domain: str, rec: dict[str, Any]) -> SnapshotStatus:
    st = SnapshotStatus(
        domain=domain,
        snapshot_id=rec.get("snapshot_id"),
        blueprint_id=rec.get("blueprint_id"),
        knowledge_folder=rec.get("knowledge_folder"),
        built_at=rec.get("built_at"),
        meta_repo_path=rec.get("meta_repo_path"),
        recorded_sha=rec.get("meta_repo_sha"),
        recorded_blueprint_hash=rec.get("blueprint_hash"),
    )

    if not st.snapshot_id:
        st.state = STATE_NO_SNAPSHOT
        st.detail = "No snapshot built yet (run: keel domain build-snapshot)."
        return st

    if not st.meta_repo_path:
        st.state = STATE_UNVERIFIABLE
        st.detail = "Snapshot registered without a meta-repo path; cannot check drift."
        return st

    meta = Path(st.meta_repo_path)
    if not meta.exists() or not blueprint_path_for(meta).exists():
        st.state = STATE_META_MISSING
        st.detail = f"Meta-repo or blueprint not found at {st.meta_repo_path}."
        return st

    st.current_sha = git_head_sha(meta)
    st.current_blueprint_hash = blueprint_hash(blueprint_path_for(meta))

    if not st.recorded_sha and not st.recorded_blueprint_hash:
        st.state = STATE_UNVERIFIABLE
        st.detail = "Snapshot has no recorded provenance (built before tracking, or via --snapshot-id)."
        return st

    sha_ok = (not st.recorded_sha) or (st.recorded_sha == st.current_sha)
    bp_ok = (not st.recorded_blueprint_hash) or (st.recorded_blueprint_hash == st.current_blueprint_hash)
    if sha_ok and bp_ok:
        st.state = STATE_OK
        st.detail = "Snapshot matches current meta-repo state."
    else:
        st.state = STATE_DRIFT
        changed = []
        if not sha_ok:
            changed.append(f"meta-repo commit {st.recorded_sha} -> {st.current_sha}")
        if not bp_ok:
            changed.append("blueprint changed")
        st.detail = "Stale: " + "; ".join(changed) + ". Rebuild with: keel domain build-snapshot."
    return st


def list_snapshots(cfg: Optional[DevinConfig] = None) -> list[SnapshotStatus]:
    """Return the snapshot status for every domain in the registry."""
    cfg = cfg or DevinConfig.load()
    out: list[SnapshotStatus] = []
    for slug, rec in sorted(cfg.domains().items()):
        out.append(_verify_record(slug, rec or {}))
    return out


def verify_snapshot(domain: str, cfg: Optional[DevinConfig] = None) -> SnapshotStatus:
    """Verify a single domain's snapshot against its meta-repo."""
    cfg = cfg or DevinConfig.load()
    return _verify_record(domain, cfg.domain(domain) or {})
