"""Domain persona skill generator — creates role-based SKILL.md files.

Generates structured Markdown skill files for a domain, scoped to different
roles (developer, QA, scrum master, business analyst). Each file becomes a
reusable context document that AI code assistants can consume.

Output layout::

    dva-skills/domains/<slug>/
    ├── DOMAIN.md   # Domain overview — repos, docs, tech stack, links
    ├── DEV.md      # Developer — code patterns, frameworks, build/deploy
    ├── QA.md       # QA — test strategy, frameworks, coverage
    ├── SM.md       # Scrum Master — Jira workflow, sprint cadence
    └── BA.md       # Business Analyst — domain glossary, AC patterns
"""

from __future__ import annotations

import json
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Role definitions
# ---------------------------------------------------------------------------

ROLES = ("domain", "dev", "qa", "sm", "ba")

ROLE_LABELS = {
    "domain": "Domain Overview",
    "dev": "Developer",
    "qa": "Quality Assurance",
    "sm": "Scrum Master",
    "ba": "Business Analyst",
}


# ---------------------------------------------------------------------------
# Context gathering helpers
# ---------------------------------------------------------------------------

def gather_domain_context(domain: dict, repos: list[dict], docs: list[dict]) -> dict[str, Any]:
    """Assemble all available domain context into a single dict."""
    return {
        "name": domain["name"],
        "product": domain["product"],
        "domain_label": domain["domain"],
        "description": domain.get("description") or "",
        "jira_project": domain.get("jira_project") or "",
        "bitbucket_project": domain.get("bitbucket_project") or "",
        "confluence_space": domain.get("confluence_space") or "",
        "managed_confluence_space": domain.get("managed_confluence_space") or "",
        "jira_dashboard": domain.get("jira_dashboard") or "",
        "confluence_url": domain.get("confluence_url") or "",
        "tags": domain.get("tags") or [],
        "repos": repos,
        "docs": docs,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Individual generators
# ---------------------------------------------------------------------------

def _header(role: str, ctx: dict) -> str:
    """Standard YAML front-matter + title."""
    label = ROLE_LABELS[role]
    name = ctx["name"]
    return textwrap.dedent(f"""\
        ---
        name: {name}-{role}
        description: >-
          {label} persona skill for the {ctx['domain_label']} domain
          ({ctx['product']} product).
        domain: {name}
        product: {ctx['product']}
        role: {role}
        generated: {ctx['generated_at']}
        ---
    """)


def generate_domain_md(ctx: dict) -> str:
    """DOMAIN.md — high-level overview."""
    lines = [_header("domain", ctx)]
    lines.append(f"# {ctx['domain_label']} Domain — {ctx['product']}\n")

    if ctx["description"]:
        lines.append(f"{ctx['description']}\n")

    # Links section
    links = []
    if ctx["jira_project"]:
        links.append(f"- **Jira Project:** {ctx['jira_project']}")
    if ctx["jira_dashboard"]:
        links.append(f"- **Jira Dashboard:** {ctx['jira_dashboard']}")
    if ctx["bitbucket_project"]:
        links.append(f"- **Bitbucket Project:** {ctx['bitbucket_project']}")
    if ctx["confluence_space"]:
        links.append(f"- **Confluence Space:** {ctx['confluence_space']}")
    if ctx["confluence_url"]:
        links.append(f"- **Confluence URL:** {ctx['confluence_url']}")
    if ctx["managed_confluence_space"]:
        links.append(f"- **Managed Confluence Space:** {ctx['managed_confluence_space']}")
    if links:
        lines.append("## Links\n")
        lines.extend(links)
        lines.append("")

    # Repos
    repos = ctx["repos"]
    if repos:
        lines.append("## Repositories\n")
        lines.append("| Slug | Name | Clone URL |")
        lines.append("|------|------|-----------|")
        for r in repos:
            slug = r.get("repo_slug", "")
            name = r.get("repo_name", slug)
            url = r.get("clone_url", "")
            lines.append(f"| {slug} | {name} | {url} |")
        lines.append("")

    # Docs
    docs = ctx["docs"]
    if docs:
        lines.append("## Tracked Documents\n")
        lines.append("| Title | Source Space | Version |")
        lines.append("|-------|-------------|---------|")
        for d in docs:
            title = d.get("title", "")
            space = d.get("source_space_key", "")
            ver = d.get("source_version", "")
            lines.append(f"| {title} | {space} | {ver} |")
        lines.append("")

    # Tags
    if ctx["tags"]:
        lines.append(f"## Tags\n\n{', '.join(ctx['tags'])}\n")

    return "\n".join(lines)


def generate_dev_md(ctx: dict) -> str:
    """DEV.md — developer persona."""
    lines = [_header("dev", ctx)]
    lines.append(f"# Developer Guide — {ctx['domain_label']} Domain\n")
    lines.append("## Overview\n")
    lines.append(
        f"This skill provides developer context for the **{ctx['domain_label']}** domain "
        f"in the **{ctx['product']}** product.\n"
    )

    repos = ctx["repos"]
    if repos:
        lines.append("## Repositories\n")
        for r in repos:
            slug = r.get("repo_slug", "")
            url = r.get("clone_url", "")
            lines.append(f"### `{slug}`\n")
            if url:
                lines.append(f"- **Clone:** `{url}`")
            onboarded = r.get("onboarded", 0)
            if onboarded:
                lines.append("- **Onboarded:** Yes — skills installed via `dva code onboard`")
            lines.append("")

    # Code conventions placeholder
    lines.append("## Code Conventions\n")
    lines.append("<!-- Auto-populated when repos are onboarded via 'dva code onboard' -->")
    lines.append("- Follow existing patterns in each repository")
    lines.append("- Use the project's established build tool and dependency manager")
    lines.append("- Prefer constructor injection over field injection (Spring Boot)")
    lines.append("")

    # PR conventions
    lines.append("## Pull Request Conventions\n")
    if ctx["jira_project"]:
        lines.append(f"- Branch naming: `feature/{ctx['jira_project']}-<ticket-number>-<short-description>`")
        lines.append(f"- PR title: `{ctx['jira_project']}-<number>: <description>`")
    lines.append("- All PRs require at least one reviewer approval")
    lines.append("- CI must pass before merge")
    lines.append("")

    # Build & deploy
    lines.append("## Build & Deploy\n")
    if ctx["bitbucket_project"]:
        lines.append(f"- **Bitbucket Project:** {ctx['bitbucket_project']}")
    lines.append("- Check each repo's `README.md` or `Makefile` for build instructions")
    lines.append("- CI/CD pipelines are defined per-repo")
    lines.append("")

    return "\n".join(lines)


def generate_qa_md(ctx: dict) -> str:
    """QA.md — quality assurance persona."""
    lines = [_header("qa", ctx)]
    lines.append(f"# QA Guide — {ctx['domain_label']} Domain\n")
    lines.append("## Overview\n")
    lines.append(
        f"Quality assurance context for the **{ctx['domain_label']}** domain "
        f"({ctx['product']} product).\n"
    )

    # Test strategy
    lines.append("## Test Strategy\n")
    lines.append("- **Unit Tests:** Required for all business logic")
    lines.append("- **Integration Tests:** Required for API endpoints and database interactions")
    lines.append("- **Contract Tests:** Recommended for inter-service communication")
    lines.append("- **E2E Tests:** For critical user flows")
    lines.append("")

    # Repos with test info
    repos = ctx["repos"]
    if repos:
        lines.append("## Repositories & Test Coverage\n")
        lines.append("| Repository | Onboarded | Test Status |")
        lines.append("|------------|-----------|-------------|")
        for r in repos:
            slug = r.get("repo_slug", "")
            onb = "✓" if r.get("onboarded") else "—"
            lines.append(f"| `{slug}` | {onb} | Check CI pipeline |")
        lines.append("")

    # Test naming
    lines.append("## Test Naming Conventions\n")
    lines.append("- Java: `Test<ClassName>` with `@Test` methods named `test_<scenario>_<expected>`")
    lines.append("- Python: `test_<module>.py` with `test_<scenario>` functions")
    lines.append("- TypeScript: `<module>.test.ts` with `describe`/`it` blocks")
    lines.append("")

    # Quality gates
    lines.append("## Quality Gates\n")
    lines.append("- All tests must pass in CI before PR merge")
    lines.append("- No new critical/blocker SonarQube issues")
    lines.append("- Code coverage should not decrease")
    lines.append("")

    return "\n".join(lines)


def generate_sm_md(ctx: dict) -> str:
    """SM.md — scrum master persona."""
    lines = [_header("sm", ctx)]
    lines.append(f"# Scrum Master Guide — {ctx['domain_label']} Domain\n")
    lines.append("## Overview\n")
    lines.append(
        f"Sprint management context for the **{ctx['domain_label']}** domain "
        f"({ctx['product']} product).\n"
    )

    # Jira info
    lines.append("## Jira Configuration\n")
    if ctx["jira_project"]:
        lines.append(f"- **Project Key:** {ctx['jira_project']}")
    if ctx["jira_dashboard"]:
        lines.append(f"- **Dashboard:** {ctx['jira_dashboard']}")
    if not ctx["jira_project"] and not ctx["jira_dashboard"]:
        lines.append("- _No Jira project configured. Use `dva domain update <name> --jira <KEY>`_")
    lines.append("")

    # Sprint workflow
    lines.append("## Sprint Workflow\n")
    lines.append("- **Sprint Duration:** 2 weeks (adjust per team)")
    lines.append("- **Ceremonies:**")
    lines.append("  - Sprint Planning (Day 1)")
    lines.append("  - Daily Standup")
    lines.append("  - Sprint Review (Last day)")
    lines.append("  - Sprint Retrospective (Last day)")
    lines.append("")

    # Story point scale
    lines.append("## Story Points\n")
    lines.append("| Points | Complexity | Examples |")
    lines.append("|--------|-----------|----------|")
    lines.append("| 1 | Trivial | Config change, copy update |")
    lines.append("| 2 | Small | Simple bug fix, minor feature |")
    lines.append("| 3 | Medium | New endpoint, moderate feature |")
    lines.append("| 5 | Large | Cross-service feature, schema change |")
    lines.append("| 8 | Extra Large | New service, major refactor |")
    lines.append("| 13 | Epic-level | Break into smaller stories |")
    lines.append("")

    # Ticket workflow
    lines.append("## Ticket Workflow\n")
    lines.append("```")
    lines.append("Open → In Progress → In Review → QA → Done")
    lines.append("```\n")
    if ctx["jira_project"]:
        lines.append(f"- Tickets: `{ctx['jira_project']}-<number>`")
    lines.append("- Move to 'In Progress' when work starts")
    lines.append("- Move to 'In Review' when PR is created")
    lines.append("- Move to 'QA' after PR merge")
    lines.append("- Move to 'Done' after verification")
    lines.append("")

    # Team repos
    repos = ctx["repos"]
    if repos:
        lines.append(f"## Repositories ({len(repos)} linked)\n")
        for r in repos:
            lines.append(f"- `{r.get('repo_slug', '')}`")
        lines.append("")

    return "\n".join(lines)


def generate_ba_md(ctx: dict) -> str:
    """BA.md — business analyst persona."""
    lines = [_header("ba", ctx)]
    lines.append(f"# Business Analyst Guide — {ctx['domain_label']} Domain\n")
    lines.append("## Overview\n")
    lines.append(
        f"Business context for the **{ctx['domain_label']}** domain "
        f"({ctx['product']} product).\n"
    )

    if ctx["description"]:
        lines.append(f"**Description:** {ctx['description']}\n")

    # Documentation
    lines.append("## Documentation\n")
    if ctx["confluence_space"]:
        lines.append(f"- **Confluence Space:** {ctx['confluence_space']}")
    if ctx["confluence_url"]:
        lines.append(f"- **Confluence URL:** {ctx['confluence_url']}")

    docs = ctx["docs"]
    if docs:
        lines.append("\n### Tracked Pages\n")
        for d in docs:
            title = d.get("title", "Untitled")
            lines.append(f"- {title}")
    elif not ctx["confluence_space"]:
        lines.append("- _No Confluence space configured. Use `dva domain update <name> --confluence <KEY>`_")
    lines.append("")

    # Acceptance criteria template
    lines.append("## Acceptance Criteria Template\n")
    lines.append("```gherkin")
    lines.append("Feature: <Feature Name>")
    lines.append("")
    lines.append("  Scenario: <Scenario Description>")
    lines.append("    Given <precondition>")
    lines.append("    When <action>")
    lines.append("    Then <expected result>")
    lines.append("    And <additional assertions>")
    lines.append("```\n")

    # Domain glossary placeholder
    lines.append("## Domain Glossary\n")
    lines.append("<!-- Populate with domain-specific terms -->")
    lines.append("| Term | Definition |")
    lines.append("|------|-----------|")
    lines.append(f"| {ctx['domain_label']} | Core domain within {ctx['product']} |")
    if ctx["jira_project"]:
        lines.append(f"| {ctx['jira_project']} | Jira project key |")
    lines.append("")

    # Stakeholder communication
    lines.append("## Stakeholder Communication\n")
    if ctx["jira_dashboard"]:
        lines.append(f"- **Dashboard:** {ctx['jira_dashboard']}")
    lines.append("- Sprint demos showcase completed features each sprint")
    lines.append("- Requirements documented in Confluence before sprint planning")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

GENERATORS = {
    "domain": generate_domain_md,
    "dev": generate_dev_md,
    "qa": generate_qa_md,
    "sm": generate_sm_md,
    "ba": generate_ba_md,
}

FILE_NAMES = {
    "domain": "DOMAIN.md",
    "dev": "DEV.md",
    "qa": "QA.md",
    "sm": "SM.md",
    "ba": "BA.md",
}


def generate_skill_files(
    ctx: dict,
    output_dir: Path,
    roles: Optional[list[str]] = None,
) -> dict[str, Path]:
    """Generate skill files for the given roles. Returns {role: path} of written files."""
    if roles is None:
        roles = list(ROLES)

    output_dir.mkdir(parents=True, exist_ok=True)
    written = {}

    for role in roles:
        gen = GENERATORS.get(role)
        if not gen:
            continue
        content = gen(ctx)
        filepath = output_dir / FILE_NAMES[role]
        filepath.write_text(content)
        written[role] = filepath

    return written
