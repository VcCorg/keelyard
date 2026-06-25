"""Resolve every enrichment input from registered CLI domain data.

Per the integration contract, `dva kg okf enrich --domain <slug>` must NOT take
manual paths. Everything is derived from what was registered when the domain and
its repos/docs were created:

  bundle_dir        <- skills/domains/<slug>/knowledge  (conventional OKF root)
  codebase_paths    <- get_domain_repos(slug) matched to onboarded get_repos() paths
  confluence_docs   <- get_domain_docs(slug)  (tracked Confluence page ids + space)
  confluence_url    <- domain.confluence_url
  confluence_space  <- domain.confluence_space
  jira_project      <- domain.jira_project
  product           <- domain.product

This module performs the lookups and best-effort path matching so the runner and
CLI never hard-code locations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agentic_cli.tracker import (
    get_domain,
    get_domain_docs,
    get_domain_repos,
    get_repos,
)


@dataclass
class DomainEnrichmentContext:
    """All enrichment inputs resolved from a domain slug."""

    slug: str
    product: str = ""
    bundle_dir: Path | None = None
    codebase_paths: list[Path] = field(default_factory=list)
    confluence_docs: list[dict[str, Any]] = field(default_factory=list)
    confluence_url: str = ""
    confluence_space: str = ""
    jira_project: str = ""
    # repos that are linked but not yet onboarded / not found on disk
    unresolved_repos: list[str] = field(default_factory=list)

    @property
    def confluence_page_ids(self) -> list[str]:
        return [d["source_page_id"] for d in self.confluence_docs if d.get("source_page_id")]


def default_bundle_dir(slug: str, base: Path | None = None) -> Path:
    """Conventional OKF bundle root for a domain slug."""
    base = base or Path.cwd()
    return base / "skills" / "domains" / slug / "knowledge"


def _match_local_path(repo: dict[str, Any], onboarded: list[dict[str, Any]]) -> Path | None:
    """Best-effort match a linked domain repo to an onboarded local path.

    `domain_repos` stores repo_slug / repo_name / clone_url but no local path.
    The `repos` registry stores local `path` + `repo_url` + `name`. We match on
    clone_url first, then on slug/name appearing in the registered name or path.
    """
    slug = (repo.get("repo_slug") or "").lower()
    name = (repo.get("repo_name") or "").lower()
    clone = (repo.get("clone_url") or "").lower()

    # 1) exact clone_url match against registered repo_url
    if clone:
        for r in onboarded:
            if (r.get("repo_url") or "").lower() == clone:
                p = Path(r["path"])
                if p.exists():
                    return p

    # 2) slug/name match against registered name or path tail
    for r in onboarded:
        rname = (r.get("name") or "").lower()
        ptail = Path(r.get("path", "")).name.lower()
        for needle in (slug, name):
            if needle and (needle == rname or needle == ptail):
                p = Path(r["path"])
                if p.exists():
                    return p
    return None


def resolve_domain_enrichment_context(
    slug: str,
    bundle_base: Path | None = None,
) -> DomainEnrichmentContext:
    """Build a fully-resolved enrichment context from registered domain data.

    Raises ValueError if the domain is not registered.
    """
    d = get_domain(slug)
    if not d:
        raise ValueError(
            f"Domain '{slug}' is not registered. "
            f"Create it first with: dva domain create <PRODUCT> <DOMAIN>"
        )

    ctx = DomainEnrichmentContext(
        slug=slug,
        product=d.get("product") or "",
        bundle_dir=default_bundle_dir(slug, bundle_base),
        confluence_url=d.get("confluence_url") or "",
        confluence_space=d.get("confluence_space") or "",
        jira_project=d.get("jira_project") or "",
    )

    # Codebase paths from linked + onboarded repos
    linked = get_domain_repos(slug)
    onboarded = get_repos(check_exists=True)
    for repo in linked:
        local = _match_local_path(repo, onboarded)
        if local is not None:
            ctx.codebase_paths.append(local)
        else:
            ctx.unresolved_repos.append(repo.get("repo_slug") or repo.get("repo_name") or "?")

    # Confluence docs tracked for the domain
    ctx.confluence_docs = get_domain_docs(slug)

    return ctx
