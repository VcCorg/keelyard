"""Domain service — thin proxy over the agentic-cli core logic.

Design principle (per project requirement):
- The dashboard NEVER re-implements domain onboarding logic.
- Reads + simple mutations import the CLI's `agentic_cli.tracker` functions directly.
- Long-running / external-API steps (fetch-repos, add-docs, gen-skills,
  init-context, init-meta) are executed by shelling out to the real `dva`
  CLI and streaming its stdout, so the Bitbucket/Confluence/git logic lives
  in exactly one place.
"""

import asyncio
import os
import shutil
import sys
from typing import AsyncGenerator, Optional

from pydantic import BaseModel


# ── Errors ──────────────────────────────────────────────────────────────────

class ProductInUseError(Exception):
    """Raised when a product cannot be removed because domains still reference it."""

    def __init__(self, product: str, domains: list[str]):
        self.product = product
        self.domains = domains
        super().__init__(
            f"Product '{product}' has {len(domains)} domain(s) assigned: "
            f"{', '.join(domains)}. Reassign or delete them first."
        )


# ── Pydantic models (transport shapes only — not logic) ─────────────────────

class ProductInfo(BaseModel):
    name: str
    description: Optional[str] = None
    tags: list[str] = []
    domain_count: int = 0


class RepoInfo(BaseModel):
    repo_slug: str
    repo_name: Optional[str] = None
    clone_url: Optional[str] = None
    onboarded: bool = False


class DocInfo(BaseModel):
    source_page_id: str
    source_space_key: Optional[str] = None
    title: Optional[str] = None
    source_version: int = 0


class DomainInfo(BaseModel):
    name: str  # slug, e.g. cwow-facility
    product: str
    domain: str  # label, e.g. Facility
    description: Optional[str] = None
    jira_project: Optional[str] = None
    jira_board: Optional[str] = None
    bitbucket_project: Optional[str] = None
    bitbucket_url: Optional[str] = None
    confluence_space: Optional[str] = None
    confluence_url: Optional[str] = None
    jira_dashboard: Optional[str] = None
    tags: list[str] = []
    kg_ingested: int = 0
    repo_count: int = 0
    doc_count: int = 0


class DomainDetail(DomainInfo):
    repos: list[RepoInfo] = []
    docs: list[DocInfo] = []


class BitbucketRepoCandidate(BaseModel):
    slug: str
    name: Optional[str] = None
    clone_url: Optional[str] = None
    already_linked: bool = False


class ConfluencePageCandidate(BaseModel):
    page_id: str
    title: Optional[str] = None
    space_key: Optional[str] = None
    version: int = 0
    already_tracked: bool = False


# ── CLI access helpers ──────────────────────────────────────────────────────

def _tracker():
    """Import the CLI tracker module (single source of truth)."""
    from agentic_cli import tracker
    return tracker


def _slugify(product: str, domain: str) -> str:
    """Mirror the CLI slug rule (product-domain, lowercase)."""
    return f"{product.lower()}-{domain.lower().replace(' ', '-')}"


def resolve_cli_command() -> list[str]:
    """Resolve how to invoke the dva CLI for subprocess streaming.

    Prefers the installed `dva` console script, falls back to running the
    module with the current interpreter.
    """
    dva = shutil.which("dva")
    if dva:
        return [dva]
    return [sys.executable, "-m", "agentic_cli.main"]


# ── Reads (library import) ──────────────────────────────────────────────────

def list_products() -> list[ProductInfo]:
    t = _tracker()
    products = t.get_products() or []
    domains = t.get_domains() or []
    counts: dict[str, int] = {}
    for d in domains:
        counts[d.get("product", "")] = counts.get(d.get("product", ""), 0) + 1
    return [
        ProductInfo(
            name=p["name"],
            description=p.get("description"),
            tags=p.get("tags") or [],
            domain_count=counts.get(p["name"], 0),
        )
        for p in products
    ]


def _product_info(name: str) -> Optional[ProductInfo]:
    t = _tracker()
    p = t.get_product(name)
    if not p:
        return None
    domains = t.get_domains(product=p["name"]) or []
    return ProductInfo(
        name=p["name"],
        description=p.get("description"),
        tags=p.get("tags") or [],
        domain_count=len(domains),
    )


def _to_domain_info(d: dict, t) -> DomainInfo:
    slug = d["name"]
    repos = t.get_domain_repos(slug) or []
    docs = t.get_domain_docs(slug) or []
    return DomainInfo(
        name=slug,
        product=d.get("product", ""),
        domain=d.get("domain", ""),
        description=d.get("description"),
        jira_project=d.get("jira_project"),
        jira_board=d.get("jira_board"),
        bitbucket_project=d.get("bitbucket_project"),
        bitbucket_url=d.get("bitbucket_url"),
        confluence_space=d.get("confluence_space"),
        confluence_url=d.get("confluence_url"),
        jira_dashboard=d.get("jira_dashboard"),
        tags=d.get("tags") or [],
        kg_ingested=d.get("kg_ingested", 0) or 0,
        repo_count=len(repos),
        doc_count=len(docs),
    )


def list_domains(product: Optional[str] = None) -> list[DomainInfo]:
    t = _tracker()
    domains = t.get_domains(product=product.upper() if product else None) or []
    return [_to_domain_info(d, t) for d in domains]


def get_domain_detail(slug: str) -> Optional[DomainDetail]:
    t = _tracker()
    d = t.get_domain(slug)
    if not d:
        return None
    base = _to_domain_info(d, t)
    repos = [
        RepoInfo(
            repo_slug=r.get("repo_slug", ""),
            repo_name=r.get("repo_name"),
            clone_url=r.get("clone_url"),
            onboarded=bool(r.get("onboarded", 0)),
        )
        for r in (t.get_domain_repos(slug) or [])
    ]
    docs = [
        DocInfo(
            source_page_id=str(dd.get("source_page_id", "")),
            source_space_key=dd.get("source_space_key"),
            title=dd.get("title"),
            source_version=dd.get("source_version", 0) or 0,
        )
        for dd in (t.get_domain_docs(slug) or [])
    ]
    return DomainDetail(**base.model_dump(), repos=repos, docs=docs)


# ── Product mutations (library import — single source of truth) ─────────────

def create_product(
    name: str,
    description: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> ProductInfo:
    """Register a product. Raises ValueError if it already exists."""
    t = _tracker()
    name_upper = name.strip().upper()
    if not name_upper:
        raise ValueError("Product name is required.")
    if t.get_product(name_upper):
        raise ValueError(f"Product '{name_upper}' already exists.")
    t.register_product(name=name_upper, description=description, tags=tags or [])
    t.record_activity(
        command="product", subcommand="create",
        args={"name": name_upper, "via": "dashboard"},
    )
    return _product_info(name_upper)


def update_product(
    name: str,
    description: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> Optional[ProductInfo]:
    """Update a product's description/tags. Returns None if not found."""
    t = _tracker()
    name_upper = name.strip().upper()
    if not t.get_product(name_upper):
        return None
    fields = {}
    if description is not None:
        fields["description"] = description
    if tags is not None:
        fields["tags"] = tags
    if fields:
        t.update_product(name_upper, **fields)
        t.record_activity(
            command="product", subcommand="update",
            args={"name": name_upper, "fields": list(fields.keys()), "via": "dashboard"},
        )
    return _product_info(name_upper)


def delete_product(name: str) -> Optional[bool]:
    """Remove a product.

    Returns None if the product doesn't exist. Raises ProductInUseError if any
    domains still reference it (mirrors `dva product remove`, which blocks).
    """
    t = _tracker()
    name_upper = name.strip().upper()
    if not t.get_product(name_upper):
        return None
    domains = t.get_domains(product=name_upper) or []
    if domains:
        raise ProductInUseError(name_upper, [d.get("name", "") for d in domains])
    removed = t.remove_product(name_upper)
    if removed:
        t.record_activity(
            command="product", subcommand="remove",
            args={"name": name_upper, "via": "dashboard"},
        )
    return removed


# ── Simple mutations (library import) ───────────────────────────────────────

def create_domain(
    domain: str,
    product: str,
    description: Optional[str] = None,
    jira_project: Optional[str] = None,
    jira_board: Optional[str] = None,
    bitbucket_project: Optional[str] = None,
    bitbucket_url: Optional[str] = None,
    confluence_space: Optional[str] = None,
    confluence_url: Optional[str] = None,
    jira_dashboard: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> DomainDetail:
    """Register a domain. Raises ValueError if the product is unknown or if
    neither a Bitbucket project key nor a Bitbucket URL is provided."""
    t = _tracker()
    product_upper = product.upper()
    if not t.get_product(product_upper):
        raise ValueError(
            f"Product '{product_upper}' not found. Register it first via 'dva product create {product_upper}'."
        )
    if not (bitbucket_project and bitbucket_project.strip()) and not (
        bitbucket_url and bitbucket_url.strip()
    ):
        raise ValueError(
            "A Bitbucket project key or a Bitbucket repo/project URL is required."
        )
    slug = _slugify(product_upper, domain)
    t.register_domain(
        name=slug,
        product=product_upper,
        domain=domain,
        description=description,
        jira_project=jira_project,
        jira_board=jira_board,
        bitbucket_project=bitbucket_project,
        bitbucket_url=bitbucket_url,
        confluence_space=confluence_space,
        jira_dashboard=jira_dashboard,
        confluence_url=confluence_url,
        tags=tags or [],
    )
    t.record_activity(
        command="domain", subcommand="create",
        args={"name": slug, "product": product_upper, "domain": domain, "via": "dashboard"},
    )
    return get_domain_detail(slug)


def update_domain(slug: str, **fields) -> Optional[DomainDetail]:
    t = _tracker()
    if not t.get_domain(slug):
        return None
    clean = {k: v for k, v in fields.items() if v is not None}
    # Reassigning to another product: validate it exists and normalize casing.
    if clean.get("product"):
        product_upper = clean["product"].upper()
        if not t.get_product(product_upper):
            raise ValueError(
                f"Product '{product_upper}' not found. Register it first."
            )
        clean["product"] = product_upper
    if clean:
        t.update_domain(slug, **clean)
        t.record_activity(
            command="domain", subcommand="update",
            args={"name": slug, "fields": list(clean.keys()), "via": "dashboard"},
        )
    return get_domain_detail(slug)


def delete_domain(slug: str) -> bool:
    t = _tracker()
    removed = t.remove_domain(slug)
    if removed:
        t.record_activity(
            command="domain", subcommand="remove",
            args={"name": slug, "via": "dashboard"},
        )
    return removed


def link_repo(slug: str, repo_slug: str, repo_name: Optional[str] = None,
              clone_url: Optional[str] = None) -> bool:
    t = _tracker()
    added = t.link_repo_to_domain(slug, repo_slug, repo_name=repo_name, clone_url=clone_url)
    if added:
        t.record_activity(
            command="domain", subcommand="link-repo",
            args={"domain": slug, "repo": repo_slug, "via": "dashboard"},
        )
    return added


def unlink_repo(slug: str, repo_slug: str) -> bool:
    t = _tracker()
    return t.unlink_repo_from_domain(slug, repo_slug)


def add_doc(slug: str, source_page_id: str, source_space_key: Optional[str] = None,
            title: Optional[str] = None, source_version: int = 0) -> bool:
    t = _tracker()
    return t.add_domain_doc(
        slug,
        source_page_id=source_page_id,
        source_space_key=source_space_key,
        title=title,
        source_version=source_version,
    )


def remove_doc(slug: str, source_page_id: str) -> bool:
    t = _tracker()
    return t.remove_domain_doc(slug, source_page_id)


# ── Candidate previews (library import — lets the UI multi-select) ──────────

def list_bitbucket_candidates(slug: str, limit: int = 500,
                              filter_text: Optional[str] = None) -> list[BitbucketRepoCandidate]:
    """Preview repos in the domain's Bitbucket project (via the same core
    function the CLI uses) so the UI can present a selectable list."""
    t = _tracker()
    d = t.get_domain(slug)
    if not d:
        raise ValueError(f"Domain '{slug}' not found.")

    from agentic_cli.mcp_tool_client import (
        bb_list_project_repos, parse_project_key, parse_bitbucket_url,
    )

    bb_project = parse_project_key(d.get("bitbucket_project") or "")
    if not bb_project:
        # Fall back to deriving the project key from the Bitbucket URL.
        bb_project, _ = parse_bitbucket_url(d.get("bitbucket_url") or "")
    if not bb_project:
        raise ValueError(f"Domain '{slug}' has no Bitbucket project key or URL.")

    repos = bb_list_project_repos(bb_project, limit=limit) or []
    repos = [
        r for r in repos
        if "deprecated" not in (r.get("slug", "") + r.get("name", "")).lower()
    ]
    if filter_text:
        ft = filter_text.lower()
        repos = [r for r in repos if ft in r.get("slug", r.get("name", "")).lower()]

    already = {r["repo_slug"] for r in (t.get_domain_repos(slug) or [])}
    out: list[BitbucketRepoCandidate] = []
    for r in repos:
        s = r.get("slug", r.get("name", ""))
        out.append(BitbucketRepoCandidate(
            slug=s,
            name=r.get("name", s),
            clone_url=r.get("clone_url_https") or r.get("clone_url_ssh") or r.get("clone_url"),
            already_linked=s in already,
        ))
    return out


def list_confluence_candidates(slug: str, limit: int = 200,
                               filter_text: Optional[str] = None) -> list[ConfluencePageCandidate]:
    """Preview pages in the domain's Confluence space/URL (via the same core
    functions the CLI uses) so the UI can present a selectable list.

    Note: this does NOT do the cross-space release-page scan that the full
    `add-docs` command performs — use the streamed `add-docs --all` for that.
    """
    t = _tracker()
    d = t.get_domain(slug)
    if not d:
        raise ValueError(f"Domain '{slug}' not found.")

    from agentic_cli.mcp_tool_client import (
        confluence_get_space_pages, confluence_get_all_descendants,
        parse_space_key, parse_confluence_url,
    )

    space_key = ""
    page_id = ""
    confluence_url = d.get("confluence_url") or ""
    if confluence_url:
        space_key, page_id = parse_confluence_url(confluence_url)
    if not space_key and not page_id:
        space_key = parse_space_key(d.get("confluence_space") or "")
    if not space_key and not page_id:
        raise ValueError(f"Domain '{slug}' has no Confluence space key or URL.")

    if page_id:
        pages = confluence_get_all_descendants(page_id) or []
    else:
        pages = confluence_get_space_pages(space_key, limit=limit) or []

    if filter_text:
        ft = filter_text.lower()
        pages = [p for p in pages if ft in (p.get("title") or "").lower()]

    already = {dd["source_page_id"] for dd in (t.get_domain_docs(slug) or [])}
    out: list[ConfluencePageCandidate] = []
    for p in pages:
        pid = str(p.get("id", ""))
        out.append(ConfluencePageCandidate(
            page_id=pid,
            title=p.get("title"),
            space_key=p.get("space", space_key),
            version=p.get("version", 0) or 0,
            already_tracked=pid in already,
        ))
    return out


# ── Long-running steps (subprocess + streaming) ─────────────────────────────

async def stream_domain_command(args: list[str]) -> AsyncGenerator[str, None]:
    """Run `dva domain <args>` and yield stdout/stderr lines as they arrive.

    This is the proxy mechanism for steps whose logic must not be duplicated
    (fetch-repos, add-docs, gen-skills, init-context, init-meta).
    """
    cmd = resolve_cli_command() + ["domain"] + args
    yield f"$ {' '.join(cmd)}"

    env = os.environ.copy()
    env["NO_COLOR"] = "1"  # keep streamed output clean for the browser
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
