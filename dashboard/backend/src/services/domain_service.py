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


def _wipe_dir(path) -> bool:
    """Best-effort recursive delete of a directory. Returns True if removed."""
    try:
        if path and path.exists() and path.is_dir():
            shutil.rmtree(path)
            return True
    except Exception:
        pass
    return False


def delete_product_cascade(name: str, wipe_meta: bool = False) -> Optional[dict]:
    """Force-remove a product and all its domains (testing/cleanup helper).

    Removes every domain registration under the product, then the product
    itself, from the tracker. When ``wipe_meta`` is set, also deletes the
    on-disk meta-repos (``domain-<slug>-meta`` for each domain and
    ``product-<slug>-meta``) so re-onboarding with the same name starts clean.

    Returns None if the product doesn't exist, else a summary dict.
    """
    t = _tracker()
    name_upper = name.strip().upper()
    if not t.get_product(name_upper):
        return None

    domains = t.get_domains(product=name_upper) or []
    deleted_domains: list[str] = []
    wiped_paths: list[str] = []

    for d in domains:
        slug = d.get("name", "")
        if not slug:
            continue
        if wipe_meta:
            meta = _resolve_domain_meta_path(slug)
            if _wipe_dir(meta):
                wiped_paths.append(str(meta))
        if t.remove_domain(slug):
            deleted_domains.append(slug)

    if wipe_meta:
        product_meta = _resolve_product_meta_path(name_upper)
        if _wipe_dir(product_meta):
            wiped_paths.append(str(product_meta))

    removed = bool(t.remove_product(name_upper))
    t.record_activity(
        command="product", subcommand="remove-cascade",
        args={
            "name": name_upper,
            "domains_removed": len(deleted_domains),
            "wipe_meta": wipe_meta,
            "via": "dashboard",
        },
    )
    return {
        "product": name_upper,
        "product_removed": removed,
        "domains_removed": deleted_domains,
        "wiped_paths": wiped_paths,
    }


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

async def _stream_cli(cmd: list[str]) -> AsyncGenerator[str, None]:
    """Run a resolved CLI command and yield stdout/stderr lines as they arrive."""
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


async def stream_domain_command(args: list[str]) -> AsyncGenerator[str, None]:
    """Run `dva domain <args>` and yield stdout/stderr lines as they arrive.

    This is the proxy mechanism for steps whose logic must not be duplicated
    (fetch-repos, add-docs, gen-skills, init-context, init-meta).
    """
    async for line in _stream_cli(resolve_cli_command() + ["domain"] + args):
        yield line


async def stream_product_command(args: list[str]) -> AsyncGenerator[str, None]:
    """Run `dva product <args>` and yield stdout/stderr lines as they arrive.

    Proxy for product-tier steps (init-meta, exceptions add) whose scaffolding
    and git logic must live in exactly one place (the CLI).
    """
    async for line in _stream_cli(resolve_cli_command() + ["product"] + args):
        yield line


# ── Product meta-repo reads (library import — governance + exceptions) ───────

class GovernanceInfo(BaseModel):
    found: bool = False
    path: Optional[str] = None
    governance: Optional[dict] = None
    crosswalk: Optional[dict] = None


class ExceptionInfo(BaseModel):
    id: str
    rule: str
    reason: str
    scope: str
    owner: str
    created_at: str = ""
    expires_at: str = ""
    status: str = "active"
    effective: bool = True


def _resolve_product_meta_path(product: str):
    """Resolve the on-disk product meta-repo path (mirrors the CLI rule)."""
    from agentic_cli.commands.domain import _get_code_workspace

    slug = product.lower()
    workspace = _get_code_workspace()
    return workspace / slug / f"product-{slug}-meta"


def _resolve_domain_meta_path(slug: str):
    """Resolve the on-disk domain meta-repo path (mirrors the CLI rule)."""
    from agentic_cli.commands.domain import _get_code_workspace

    workspace = _get_code_workspace()
    return workspace / slug / f"domain-{slug}-meta"


def _resolve_domain_context_path(slug: str):
    """Resolve the on-disk domain context-repo path (mirrors the CLI rule).

    Matches ``domain init-context`` default: ``<workspace>/<slug>/<slug>-domain-context``.
    """
    from agentic_cli.commands.domain import _get_code_workspace

    workspace = _get_code_workspace()
    return workspace / slug / f"{slug}-domain-context"


class ScaffoldRepoPath(BaseModel):
    kind: str  # "context" | "meta"
    path: str
    exists: bool


class ScaffoldPaths(BaseModel):
    context: ScaffoldRepoPath
    meta: ScaffoldRepoPath


def get_scaffold_paths(slug: str) -> ScaffoldPaths:
    """Resolve the domain context-repo and meta-repo paths + existence.

    Lets the dashboard offer an "Open in IDE" action to review the generated
    files once a scaffold step has run.
    """
    ctx = _resolve_domain_context_path(slug)
    meta = _resolve_domain_meta_path(slug)

    def _exists(p) -> bool:
        return bool(p.exists() and p.is_dir() and any(p.iterdir()))

    return ScaffoldPaths(
        context=ScaffoldRepoPath(kind="context", path=str(ctx), exists=_exists(ctx)),
        meta=ScaffoldRepoPath(kind="meta", path=str(meta), exists=_exists(meta)),
    )


# ── Persona skills: review + catalog (library import) ────────────────────────

class GeneratedPersonaInfo(BaseModel):
    id: str
    title: str
    source: str  # "built-in" | "product"
    path: str
    bytes: int = 0


class PersonaCatalogInfo(BaseModel):
    id: str
    label: str
    source: str  # "built-in" | "product"
    ai_enrich: bool = False


def _persona_title(text: str, fallback: str) -> str:
    """Extract a human title from a SKILL.md (front-matter description or H1)."""
    lines = text.splitlines()
    # front-matter description
    in_fm = False
    for i, line in enumerate(lines):
        if line.strip() == "---":
            in_fm = not in_fm
            continue
        if in_fm and line.strip().startswith("description:"):
            desc = line.split(":", 1)[1].strip().lstrip(">-").strip()
            if desc:
                return desc
        if not in_fm and line.startswith("# "):
            return line[2:].strip()
    return fallback


def list_generated_personas(slug: str) -> list[GeneratedPersonaInfo]:
    """List persona SKILL.md files generated into a domain meta-repo."""
    from agentic_cli.meta_repo.config import BUILTIN_PERSONA_IDS

    meta = _resolve_domain_meta_path(slug)
    personas_dir = meta / ".agents" / "skills" / "personas"
    if not personas_dir.exists():
        return []

    out: list[GeneratedPersonaInfo] = []
    for d in sorted(p for p in personas_dir.iterdir() if p.is_dir()):
        skill_file = d / "SKILL.md"
        if not skill_file.is_file():
            continue
        text = skill_file.read_text(encoding="utf-8", errors="replace")
        out.append(GeneratedPersonaInfo(
            id=d.name,
            title=_persona_title(text, d.name),
            source="built-in" if d.name in BUILTIN_PERSONA_IDS else "product",
            path=str(skill_file),
            bytes=skill_file.stat().st_size,
        ))
    return out


def get_persona_content(slug: str, persona_id: str) -> Optional[str]:
    """Return the raw SKILL.md content for a generated persona (review)."""
    meta = _resolve_domain_meta_path(slug)
    skill_file = meta / ".agents" / "skills" / "personas" / persona_id / "SKILL.md"
    if not skill_file.is_file():
        return None
    return skill_file.read_text(encoding="utf-8", errors="replace")


def list_product_personas_catalog(product: str) -> list[PersonaCatalogInfo]:
    """Resolve the effective persona catalog for a product (built-ins + customs)."""
    from agentic_cli.persona_catalog import resolve_personas

    meta = _resolve_product_meta_path(product)
    specs = resolve_personas(meta if meta.exists() else None)
    return [
        PersonaCatalogInfo(
            id=s.id,
            label=s.label,
            source="built-in" if s.builtin else "product",
            ai_enrich=s.ai_enrich,
        )
        for s in specs
    ]


def add_product_persona_entry(
    product: str,
    persona_id: str,
    label: str,
    description: Optional[str] = None,
    sections: Optional[list[dict]] = None,
    ai_enrich: bool = False,
) -> PersonaCatalogInfo:
    """Add (or replace) a product-specific persona in personas.yaml. Admin action."""
    from agentic_cli.meta_repo.config import PersonaSection, PersonaSpec
    from agentic_cli.persona_catalog import add_product_persona

    meta = _resolve_product_meta_path(product)
    if not meta.exists():
        raise ValueError(
            f"Product meta-repo not found at {meta}. Create it first (product init-meta)."
        )
    spec = PersonaSpec(
        id=persona_id.strip().lower(),
        label=label,
        description=description or "",
        sections=[
            PersonaSection(title=s.get("title", ""), body=s.get("body", ""))
            for s in (sections or [])
        ],
        ai_enrich=ai_enrich,
    )
    add_product_persona(meta, spec)
    try:
        _tracker().record_activity(
            command="product", subcommand="persona-add",
            args={"name": product.upper(), "id": spec.id, "via": "dashboard"},
        )
    except Exception:
        pass
    return PersonaCatalogInfo(
        id=spec.id, label=spec.label, source="product", ai_enrich=spec.ai_enrich
    )


def remove_product_persona_entry(product: str, persona_id: str) -> bool:
    """Remove a product-specific persona from personas.yaml. Admin action."""
    from agentic_cli.persona_catalog import remove_product_persona

    meta = _resolve_product_meta_path(product)
    if not meta.exists():
        return False
    removed = remove_product_persona(meta, persona_id.lower())
    if removed:
        try:
            _tracker().record_activity(
                command="product", subcommand="persona-remove",
                args={"name": product.upper(), "id": persona_id.lower(), "via": "dashboard"},
            )
        except Exception:
            pass
    return removed


async def stream_product_regen_personas(
    product: str, enrich: bool = False
) -> AsyncGenerator[str, None]:
    """Regenerate personas across every domain in a product. Admin action.

    Runs `dva domain regen-personas <slug>` for each domain under the product,
    streaming a combined log. Emits a single final __EXIT__ at the end.
    """
    domains = _tracker().get_domains(product=product.upper()) or []
    if not domains:
        yield f"No domains registered for product '{product.upper()}'."
        yield "__EXIT__ 0"
        return

    base = resolve_cli_command() + ["domain"]
    worst_rc = 0
    for d in domains:
        slug = d.get("name", "")
        yield f"=== {slug} ==="
        args = ["regen-personas", slug]
        if enrich:
            args.append("--enrich")
        async for line in _stream_cli(base + args):
            if line.startswith("__EXIT__"):
                try:
                    rc = int(line.split(" ", 1)[1].strip())
                except (IndexError, ValueError):
                    rc = 0
                worst_rc = worst_rc or rc
                continue
            yield line
    yield f"__EXIT__ {worst_rc}"


def get_product_governance(product: str) -> GovernanceInfo:
    """Read governance.yaml + crosswalk.yaml from the product meta-repo."""
    import yaml

    meta_path = _resolve_product_meta_path(product)
    config_dir = meta_path / ".platform" / "config"
    if not config_dir.exists():
        return GovernanceInfo(found=False, path=str(meta_path))

    governance = None
    crosswalk = None
    gov_file = config_dir / "governance.yaml"
    cw_file = config_dir / "crosswalk.yaml"
    if gov_file.exists():
        governance = yaml.safe_load(gov_file.read_text(encoding="utf-8")) or {}
    if cw_file.exists():
        crosswalk = yaml.safe_load(cw_file.read_text(encoding="utf-8")) or {}
    return GovernanceInfo(
        found=True, path=str(meta_path), governance=governance, crosswalk=crosswalk
    )


def list_product_exceptions(product: str) -> list[ExceptionInfo]:
    """List waivers from the product meta-repo's exceptions ledger."""
    from agentic_cli.meta_repo import list_exceptions

    meta_path = _resolve_product_meta_path(product)
    if not meta_path.exists():
        return []
    entries = list_exceptions(meta_path)
    return [
        ExceptionInfo(
            id=e.id, rule=e.rule, reason=e.reason, scope=e.scope, owner=e.owner,
            created_at=e.created_at, expires_at=e.expires_at, status=e.status,
            effective=e.is_effective(),
        )
        for e in entries
    ]


def add_product_exception(
    product: str,
    rule: str,
    reason: str,
    scope: str,
    owner: str,
    expires: str = "",
) -> ExceptionInfo:
    """Record a governance waiver (library import — local file write).

    Raises ValueError if the product meta-repo doesn't exist yet.
    """
    from agentic_cli.meta_repo import add_exception
    from agentic_cli import tracker

    meta_path = _resolve_product_meta_path(product)
    if not meta_path.exists():
        raise ValueError(
            f"Product meta-repo not found at {meta_path}. "
            f"Create it first (product init-meta)."
        )
    e = add_exception(
        meta_repo_path=meta_path, rule=rule, reason=reason,
        scope=scope, owner=owner, expires_at=expires,
    )
    try:
        tracker.record_activity(
            command="product", subcommand="exceptions-add",
            args={"name": product.upper(), "rule": rule, "scope": scope,
                  "id": e.id, "via": "dashboard"},
        )
    except Exception:
        pass
    return ExceptionInfo(
        id=e.id, rule=e.rule, reason=e.reason, scope=e.scope, owner=e.owner,
        created_at=e.created_at, expires_at=e.expires_at, status=e.status,
        effective=e.is_effective(),
    )
