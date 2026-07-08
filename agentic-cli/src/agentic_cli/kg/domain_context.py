"""Query domain context from KG and build domain-aware context documents.

This module queries the Knowledge Graph (via LightRAG/Neo4j) for domain-specific
business context — SLAs, integrations, security policies, architecture — and
produces structured documents that are embedded into skills and domain-context
repositories during code onboarding.

Used by:
  - ``keel code onboard --domain <slug>``  → embed domain KG context into skills
  - ``keel domain init-context``           → bootstrap domain context repo
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# KG query helpers
# ---------------------------------------------------------------------------

def _query_lightrag(query: str, lightrag_url: str, limit: int = 10) -> Optional[str]:
    """Query LightRAG for semantic domain context. Returns text or None."""
    try:
        from agentic_cli.kg.lightrag_client import LightRAGClient
        client = LightRAGClient(base_url=lightrag_url)
        try:
            health = client.health_check()
            if not health:
                return None
            result = client.query(query, mode="hybrid", top_k=limit)
            return result.get("response") or result.get("result") or None
        finally:
            client.close()
    except Exception as e:
        logger.warning(f"LightRAG query failed: {e}")
        return None


def query_domain_kg(
    domain: str,
    aspects: Optional[list[str]] = None,
    lightrag_url: Optional[str] = None,
) -> dict[str, Any]:
    """Query the KG for all domain context aspects.

    Args:
        domain: Domain slug (e.g. "cwow-facility").
        aspects: Which aspects to query. Default: all.
        lightrag_url: LightRAG server URL (deprecated, uses KGConfig instead).

    Returns:
        Dict keyed by aspect name with KG content for each.
    """
    from agentic_cli.kg.config import KGConfig
    
    # Load KG config to determine provider
    kg_config = KGConfig.load()
    provider = kg_config.provider
    
    all_aspects = {
        "business_context": f"business requirements, domain model, key entities for {domain}",
        "slas": f"SLA requirements, response time, availability, uptime for {domain}",
        "integrations": f"integration specifications, APIs, endpoints, authentication for {domain}",
        "security": f"security policies, compliance, encryption, HIPAA, access control for {domain}",
        "performance": f"performance requirements, concurrent users, latency, throughput for {domain}",
        "architecture": f"architecture patterns, CQRS, event sourcing, microservices for {domain}",
    }

    if aspects:
        selected = {k: v for k, v in all_aspects.items() if k in aspects}
    else:
        selected = all_aspects

    results: dict[str, Any] = {}
    
    if provider == "neo4j":
        # Query Neo4j for domain context
        for aspect, query_text in selected.items():
            content = _query_neo4j(query_text, kg_config)
            results[aspect] = content or ""
    elif provider == "lightrag":
        # Query LightRAG for domain context
        lightrag_url = lightrag_url or kg_config.lightrag_url
        for aspect, query_text in selected.items():
            content = _query_lightrag(query_text, lightrag_url)
            results[aspect] = content or ""
    else:
        logger.warning(f"Unsupported KG provider: {provider}")
        for aspect in selected:
            results[aspect] = ""

    return results


def _query_neo4j(query: str, config) -> Optional[str]:
    """Query Neo4j for semantic domain context. Returns text or None."""
    try:
        from agentic_cli.kg.neo4j_client import Neo4jClient
        client = Neo4jClient(config=config)
        try:
            client.connect()
            # Simple text search in Neo4j
            cypher = """
            MATCH (n:Document)
            WHERE n.content CONTAINS $search_text
            RETURN n.content AS content
            LIMIT 5
            """
            records = client.execute_cypher(cypher, {"search_text": query})
            if records:
                return "\n\n".join([r.get("content", "") for r in records if r.get("content")])
            return None
        finally:
            client.close()
    except Exception as e:
        logger.warning(f"Neo4j query failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Domain context document builder
# ---------------------------------------------------------------------------

def build_domain_context_document(
    domain: str,
    domain_data: Optional[dict] = None,
    kg_context: Optional[dict[str, Any]] = None,
    repos: Optional[list[dict]] = None,
) -> str:
    """Build a rich Markdown domain context document from KG + metadata.

    This document is saved to the domain-context repo and referenced by
    individual repos via git submodules.

    Args:
        domain: Domain slug.
        domain_data: Domain registration data from tracker (optional).
        kg_context: KG query results from query_domain_kg (optional).
        repos: List of repo dicts linked to the domain (optional).

    Returns:
        Markdown string for kg-context.md in domain-context repo.
    """
    domain_data = domain_data or {}
    kg_context = kg_context or {}
    repos = repos or []
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    sections: list[str] = []

    # Header
    domain_label = domain_data.get("domain", domain)
    product = domain_data.get("product", "")
    sections.append(f"# Domain Context: {domain_label}\n")
    sections.append(
        f"> Domain: **{domain}**{f' | Product: **{product}**' if product else ''}\n"
        f"> Generated: {timestamp}\n"
        f"> Source: Knowledge Graph (LightRAG + Neo4j)\n"
    )

    # Domain overview
    sections.append("## Domain Overview\n")
    desc = domain_data.get("description", "")
    if desc:
        sections.append(f"{desc}\n")
    overview = [
        ("Product", product),
        ("Jira Project", domain_data.get("jira_project", "")),
        ("Bitbucket Project", domain_data.get("bitbucket_project", "")),
        ("Confluence Space", domain_data.get("confluence_space", "")),
    ]
    for label, val in overview:
        if val:
            sections.append(f"- **{label}**: {val}")
    sections.append("")

    # Linked repositories
    if repos:
        sections.append(f"## Repositories ({len(repos)})\n")
        sections.append("| Repo | Type | Onboarded |")
        sections.append("|------|------|-----------|")
        for r in repos:
            slug = r.get("repo_slug", r.get("name", "unknown"))
            onboarded = "Yes" if r.get("onboarded") else "No"
            repo_type = r.get("repo_type", "—")
            sections.append(f"| `{slug}` | {repo_type} | {onboarded} |")
        sections.append("")

    # KG-sourced business context
    if kg_context.get("business_context"):
        sections.append("## Business Context\n")
        sections.append(f"{kg_context['business_context']}\n")

    # SLAs
    if kg_context.get("slas"):
        sections.append("## SLA Requirements\n")
        sections.append(f"{kg_context['slas']}\n")

    # Integrations
    if kg_context.get("integrations"):
        sections.append("## Integration Specifications\n")
        sections.append(f"{kg_context['integrations']}\n")

    # Security
    if kg_context.get("security"):
        sections.append("## Security & Compliance\n")
        sections.append(f"{kg_context['security']}\n")

    # Performance
    if kg_context.get("performance"):
        sections.append("## Performance Requirements\n")
        sections.append(f"{kg_context['performance']}\n")

    # Architecture
    if kg_context.get("architecture"):
        sections.append("## Architecture Patterns\n")
        sections.append(f"{kg_context['architecture']}\n")

    # No KG data fallback
    if not any(kg_context.values()):
        sections.append("## Business Context\n")
        sections.append(
            "_No business context found in Knowledge Graph yet._\n\n"
            "To populate domain knowledge:\n"
            "1. Register knowledge sources: `keel data create --name <name> --source-type doc --source-location /path --project <project>`\n"
            "2. Ingest into KG: `keel kg ingest submit --source <name>`\n"
            "3. Re-run: `keel domain init-context <domain>`\n"
        )

    # Tags
    tags = domain_data.get("tags", [])
    if tags:
        sections.append(f"## Tags\n")
        sections.append(f"{', '.join(tags)}\n")

    return "\n".join(sections)


def build_domain_metadata(
    domain: str,
    domain_data: Optional[dict] = None,
    repos: Optional[list[dict]] = None,
    domain_context_repo: Optional[str] = None,
) -> dict[str, Any]:
    """Build .domain-context.json metadata for individual repos.

    This file is written to each repo during onboarding so Windsurf and
    other tools know how to locate the domain context.

    Args:
        domain: Domain slug.
        domain_data: Domain registration data from tracker.
        repos: List of repo dicts.
        domain_context_repo: Git URL of the central domain context repo.

    Returns:
        Metadata dict to be saved as .domain-context.json.
    """
    domain_data = domain_data or {}
    repos = repos or []

    return {
        "domain": domain,
        "product": domain_data.get("product", ""),
        "domain_label": domain_data.get("domain", domain),
        "description": domain_data.get("description", ""),
        "domain_context_repo": domain_context_repo or "",
        "domain_context_path": "./.domain-context",
        "domain_skills_path": "./.skills/domain",
        "jira_project": domain_data.get("jira_project", ""),
        "bitbucket_project": domain_data.get("bitbucket_project", ""),
        "confluence_space": domain_data.get("confluence_space", ""),
        "repos": [r.get("repo_slug", "") for r in repos],
        "kg_aspects": [
            "business_context", "slas", "integrations",
            "security", "performance", "architecture",
        ],
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def build_domain_skill_md(
    domain: str,
    domain_data: Optional[dict] = None,
    kg_context: Optional[dict[str, Any]] = None,
    repo_type: str = "",
) -> str:
    """Build a domain-context SKILL.md for embedding in individual repos.

    This skill file is placed in .skills/domain-context/SKILL.md and tells
    AI assistants how to use the domain knowledge during development.

    Args:
        domain: Domain slug.
        domain_data: Domain registration data.
        kg_context: KG query results.
        repo_type: Type of repo (query, command, events, api).

    Returns:
        SKILL.md content string.
    """
    domain_data = domain_data or {}
    kg_context = kg_context or {}
    domain_label = domain_data.get("domain", domain)
    product = domain_data.get("product", "")
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    lines: list[str] = []

    # Front matter
    lines.append("---")
    lines.append(f"name: {domain}-domain-context")
    lines.append(f"description: >-")
    lines.append(f"  Domain business context for {domain_label} ({product}).")
    lines.append(f"  Provides SLAs, integrations, security policies, and architecture")
    lines.append(f"  constraints from the Knowledge Graph.")
    lines.append(f"domain: {domain}")
    if repo_type:
        lines.append(f"repo_type: {repo_type}")
    lines.append(f"generated_at: {timestamp}")
    lines.append("---\n")

    # Title
    lines.append(f"# {domain_label} Domain Context\n")

    # Overview
    lines.append("## Overview\n")
    desc = domain_data.get("description", "")
    if desc:
        lines.append(f"{desc}\n")
    lines.append(
        f"This skill provides business context for the **{domain_label}** domain"
        f"{f' ({product} product)' if product else ''}. "
        f"Context is sourced from the Knowledge Graph and should be consulted "
        f"before starting any development task.\n"
    )

    # MCP tool instructions
    lines.append("## How to Use (MCP Tools)\n")
    lines.append("Before starting any coding task, query the KG MCP server:\n")
    lines.append(f"1. **Domain overview**: `query_domain_context(domain=\"{domain}\")`")
    lines.append(f"2. **SLA requirements**: `get_domain_slas(domain=\"{domain}\")`")
    lines.append(f"3. **Integrations**: `get_domain_integrations(domain=\"{domain}\")`")
    lines.append(f"4. **Security policies**: `get_domain_security_policies(domain=\"{domain}\")`")
    lines.append(f"5. **Search specifics**: `search_business_context(query=\"<your task>\")`\n")
    lines.append("> If MCP tools are unavailable, use the embedded context below.\n")

    # Embedded KG context
    lines.append("## Embedded Business Context\n")
    lines.append("_The following context was extracted from the Knowledge Graph at onboard time._\n")

    if kg_context.get("business_context"):
        lines.append("### Business Requirements\n")
        lines.append(f"{kg_context['business_context']}\n")

    if kg_context.get("slas"):
        lines.append("### SLA Requirements\n")
        lines.append(f"{kg_context['slas']}\n")

    if kg_context.get("integrations"):
        lines.append("### Integration Specifications\n")
        lines.append(f"{kg_context['integrations']}\n")

    if kg_context.get("security"):
        lines.append("### Security & Compliance\n")
        lines.append(f"{kg_context['security']}\n")

    if kg_context.get("architecture"):
        lines.append("### Architecture Patterns\n")
        lines.append(f"{kg_context['architecture']}\n")

    if not any(kg_context.values()):
        lines.append(
            "_No business context found in KG. Use MCP tools to query at runtime, "
            "or populate the KG with `keel kg ingest`._\n"
        )

    # Domain context repo reference
    lines.append("## Domain Context Repository\n")
    lines.append(
        "This repo references a central domain-context repository via git submodule.\n"
        "The domain context repo contains shared knowledge across all domain repos.\n\n"
        "- **Shared context**: `.domain-context/` (git submodule)\n"
        "- **Shared skills**: `.skills/domain/` (git submodule)\n"
        "- **Config**: `.domain-context.json`\n\n"
        "To update domain context:\n"
        "```bash\n"
        "git submodule update --remote\n"
        "```\n"
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Domain context repo scaffolding
# ---------------------------------------------------------------------------

def scaffold_domain_context_repo(
    output_dir: Path,
    domain: str,
    domain_data: Optional[dict] = None,
    kg_context: Optional[dict[str, Any]] = None,
    repos: Optional[list[dict]] = None,
    code_assist_tool: str = "generic",
) -> dict[str, Path]:
    """Create the directory structure for a domain context repository.

    Generates:
      .domain/kg-context.md, domain-metadata.json, architecture.md
      <skills_dir>/<domain>-domain-skill/SKILL.md (or .md for Windsurf)
      README.md

    Args:
        output_dir: Where to create the repo structure.
        domain: Domain slug.
        domain_data: Domain registration data.
        kg_context: KG query results.
        repos: Linked repos.
        code_assist_tool: Code assist tool (windsurf, cursor, or generic).

    Returns:
        Dict mapping file names to paths of created files.
    """
    domain_data = domain_data or {}
    kg_context = kg_context or {}
    repos = repos or []
    created: dict[str, Path] = {}

    # .domain/ directory
    domain_dir = output_dir / ".domain"
    domain_dir.mkdir(parents=True, exist_ok=True)

    # .domain/kg-context.md
    kg_context_md = build_domain_context_document(domain, domain_data, kg_context, repos)
    kg_path = domain_dir / "kg-context.md"
    kg_path.write_text(kg_context_md)
    created["kg-context.md"] = kg_path

    # .domain/domain-metadata.json
    metadata = build_domain_metadata(domain, domain_data, repos)
    meta_path = domain_dir / "domain-metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2))
    created["domain-metadata.json"] = meta_path

    # .domain/architecture.md
    arch_content = f"# {domain_data.get('domain', domain)} Architecture\n\n"
    if kg_context.get("architecture"):
        arch_content += f"{kg_context['architecture']}\n"
    else:
        arch_content += "_Architecture details will be populated from the Knowledge Graph._\n"
    arch_path = domain_dir / "architecture.md"
    arch_path.write_text(arch_content)
    created["architecture.md"] = arch_path

    # Shared domain skill - location depends on code_assist_tool.
    # NOTE: Windsurf/Cascade skills are full SKILL.md folders (NOT
    # .windsurf/workflows, which is the slash-command feature). Windsurf uses
    # the same .skills layout as generic; the install step bridges it into the
    # per-user dir Cascade scans.
    if code_assist_tool == "devin":
        # Devin project skill format: .devin/skills/<domain>-domain-skill/SKILL.md
        skills_dir = output_dir / ".devin" / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        skill_path = skills_dir / f"{domain}-domain-skill" / "SKILL.md"
    else:
        # Generic/Cursor/Windsurf format: .skills/<domain>-domain-skill/SKILL.md
        # (top-level so the Windsurf bridge discovers it).
        skills_dir = output_dir / ".skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        skill_path = skills_dir / f"{domain}-domain-skill" / "SKILL.md"

    # Shared skill content
    skill_content = build_domain_skill_md(domain, domain_data, kg_context)
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(skill_content)
    created["shared-skill.md"] = skill_path

    # README.md
    domain_label = domain_data.get("domain", domain)
    product = domain_data.get("product", "")
    repo_list = "\n".join(f"- `{r.get('repo_slug', 'unknown')}`" for r in repos) or "- _(none linked yet)_"

    # Structure description based on code_assist_tool
    if code_assist_tool == "windsurf":
        structure = f"""```
.domain/
├── kg-context.md          # Shared business context from Knowledge Graph
├── domain-metadata.json   # Domain metadata and configuration
└── architecture.md        # Domain architecture patterns

.windsurf/
└── workflows/
    ├── {domain}-domain-skill.md  # Domain context skill for AI assistants
    └── <superpowers-skills>.md  # Superpowers skills (if bootstrapped)
```"""
    else:
        structure = f"""```
.domain/
├── kg-context.md          # Shared business context from Knowledge Graph
├── domain-metadata.json   # Domain metadata and configuration
└── architecture.md        # Domain architecture patterns

.skills/
└── shared/
    └── {domain}-domain-skill/
        └── SKILL.md       # Domain context skill for AI assistants
```"""

    readme_content = f"""# {domain_label} Domain Context

> Product: {product or '—'} | Domain: {domain}

This repository contains shared domain knowledge and skills for the **{domain_label}** domain.

## Structure

{structure}

## Linked Repositories

{repo_list}

## Usage

This repository is referenced as a git submodule in individual repositories.

### For Developers

```bash
# Clone a repo with domain context
git clone --recurse-submodules https://github.com/company/<repo>.git

# Or initialize submodules after cloning
git submodule update --init --recursive

# Update domain context to latest
git submodule update --remote
```

### Updating Domain Context

1. Update files in this repository
2. Commit and push changes
3. Individual repos pull updates via `git submodule update --remote`

## Regenerating Context

```bash
# Re-query KG and regenerate domain context
keel domain init-context {domain}
```
"""
    readme_path = output_dir / "README.md"
    readme_path.write_text(readme_content)
    created["README.md"] = readme_path

    return created
