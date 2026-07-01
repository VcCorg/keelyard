"""OKF bundle provenance & freshness.

When an OKF bundle is built from graphify graphs, we stamp it with a small
``.okf-provenance.json`` recording, per repo, the SHA-256 of the ``graph.json``
the bundle was generated from. A later freshness check re-hashes each repo's
current ``graph.json`` and compares: if a hash differs (code changed and the
graph was refreshed), the bundle is **stale** and should be re-enriched.

This is the deterministic signal the team workflow needs so the dashboard can
flag "repo X changed since last enrich" without any model call.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentic_cli.kg.okf.schema import slugify

PROVENANCE_FILE = ".okf-provenance.json"
SCHEMA = "okf-provenance/v1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def graph_json_path(repo_path: Path) -> Path:
    return Path(repo_path) / "graphify-out" / "graph.json"


def graph_hash(repo_path: Path) -> str | None:
    """SHA-256 of a repo's ``graphify-out/graph.json`` (None if absent)."""
    p = graph_json_path(repo_path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def write_provenance(
    bundle_dir: Path,
    repo_paths: list[Path],
    *,
    code_source: str = "graphify",
    source: str = "both",
    enriched_at: str | None = None,
) -> Path:
    """Stamp the bundle with the graph hashes it was built from."""
    repos: list[dict[str, Any]] = []
    for rp in repo_paths:
        rp = Path(rp)
        repos.append({
            "repo": rp.name,
            "namespace": slugify(rp.name),
            "path": str(rp.resolve()),
            "graph_hash": graph_hash(rp),
            "graph_path": str(graph_json_path(rp)),
        })
    data = {
        "schema": SCHEMA,
        "enriched_at": enriched_at or _now_iso(),
        "code_source": code_source,
        "source": source,
        "repos": repos,
    }
    out = Path(bundle_dir) / PROVENANCE_FILE
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return out


def read_provenance(bundle_dir: Path) -> dict[str, Any] | None:
    p = Path(bundle_dir) / PROVENANCE_FILE
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


@dataclass
class RepoFreshness:
    repo: str
    status: str  # fresh | stale | missing-graph | new | removed
    stored_hash: str | None = None
    current_hash: str | None = None


@dataclass
class FreshnessReport:
    bundle_dir: Path
    has_provenance: bool
    stale: bool
    enriched_at: str | None = None
    repos: list[RepoFreshness] = field(default_factory=list)

    @property
    def stale_repos(self) -> list[str]:
        return [r.repo for r in self.repos if r.status != "fresh"]

    @property
    def summary(self) -> str:
        if not self.has_provenance:
            return "no provenance (never enriched from graphify, or pre-dates tracking)"
        if not self.stale:
            return "fresh"
        return f"stale: {', '.join(self.stale_repos)}"


def check_freshness(bundle_dir: Path, repo_paths: list[Path]) -> FreshnessReport:
    """Compare current repo graph hashes against the bundle's provenance.

    A bundle is stale when any repo's current ``graph.json`` hash differs from
    the stored hash, when a new repo has been added, or when a tracked repo's
    graph is now missing.
    """
    prov = read_provenance(bundle_dir)
    current = {slugify(Path(p).name): Path(p) for p in repo_paths}

    if not prov:
        # No provenance: treat every current repo as new/unknown -> stale.
        repos = [
            RepoFreshness(repo=p.name, status="new", current_hash=graph_hash(p))
            for p in current.values()
        ]
        return FreshnessReport(
            bundle_dir=Path(bundle_dir), has_provenance=False,
            stale=bool(repos), enriched_at=None, repos=repos,
        )

    stored = {r.get("namespace") or slugify(r.get("repo", "")): r for r in prov.get("repos", [])}
    seen: set[str] = set()
    out: list[RepoFreshness] = []

    for ns, path in current.items():
        seen.add(ns)
        cur = graph_hash(path)
        rec = stored.get(ns)
        if rec is None:
            out.append(RepoFreshness(repo=path.name, status="new", current_hash=cur))
        elif cur is None:
            out.append(RepoFreshness(repo=path.name, status="missing-graph",
                                     stored_hash=rec.get("graph_hash"), current_hash=None))
        elif cur != rec.get("graph_hash"):
            out.append(RepoFreshness(repo=path.name, status="stale",
                                     stored_hash=rec.get("graph_hash"), current_hash=cur))
        else:
            out.append(RepoFreshness(repo=path.name, status="fresh",
                                     stored_hash=rec.get("graph_hash"), current_hash=cur))

    # Repos that were enriched before but are no longer linked/resolved.
    for ns, rec in stored.items():
        if ns not in seen:
            out.append(RepoFreshness(repo=rec.get("repo", ns), status="removed",
                                     stored_hash=rec.get("graph_hash")))

    stale = any(r.status != "fresh" for r in out)
    return FreshnessReport(
        bundle_dir=Path(bundle_dir), has_provenance=True, stale=stale,
        enriched_at=prov.get("enriched_at"), repos=out,
    )
