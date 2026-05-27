"""Project Context Skill generator — creates a single root skill for the project.

This replaces the dependency-based skill matching with a unified project context skill
that provides access to graphify (code structure), dva-kg-mcp (requirements), and
anchor mcp (jira, bitbucket, confluence) with glean fallback.
"""

from pathlib import Path
from typing import Any

from agentic_cli.analyzer.detector import ProjectAnalysis


def generate_project_context_skill(
    project_path: Path,
    analysis: ProjectAnalysis,
    domain: str | None = None,
    product: str | None = None,
) -> dict[str, Any]:
    """Generate a project context skill configuration.

    This creates a single root skill that provides unified access to:
    - graphify: Code structure and architecture queries
    - dva-kg-mcp: Requirements and release-specific context
    - anchor mcp: Jira, Bitbucket, Confluence for project artifacts
    - glean: Fallback for general knowledge

    Args:
        project_path: Path to the project repository
        analysis: Project analysis results
        domain: Optional domain name (e.g., "cwow-facility")
        product: Optional product name (e.g., "CWOW")

    Returns:
        Skill configuration dictionary for registry.json
    """
    project_name = project_path.name

    # Build MCP configuration with fallback chain
    mcp_config = {
        "server": "multi",  # Indicates this skill uses multiple MCP servers
        "servers": [
            {
                "name": "graphify",
                "purpose": "code-structure",
                "description": "Query codebase structure and architecture using graphify knowledge graph",
                "fallback": False,
            },
            {
                "name": "dva-kg-mcp",
                "purpose": "requirements",
                "description": "Access domain requirements, release specifications, and business context",
                "fallback": False,
                "params": {
                    "domain": domain,
                    "product": product,
                },
            },
            {
                "name": "anchor",
                "purpose": "project-artifacts",
                "description": "Access Jira issues, Bitbucket PRs, and Confluence documentation",
                "fallback": False,
                "params": {
                    "jira": True,
                    "bitbucket": True,
                    "confluence": True,
                },
            },
            {
                "name": "glean",
                "purpose": "general-knowledge",
                "description": "Fallback for general company knowledge when other sources fail",
                "fallback": True,
            },
        ],
        "fallback_chain": ["dva-kg-mcp", "anchor", "glean"],
    }

    # Build auto_detect rules (minimal - only for project identification)
    auto_detect = {
        "project_name": project_name,
        "languages": analysis.languages,
        "frameworks": analysis.frameworks,
    }

    # Build tags
    tags = [
        "project-context",
        "root-skill",
    ]
    if domain:
        tags.append(f"domain:{domain}")
    if product:
        tags.append(f"product:{product}")
    tags.extend(analysis.languages)
    tags.extend(analysis.frameworks)

    skill_config = {
        "name": f"{project_name}-context",
        "description": f"Project context skill for {project_name}. Provides unified access to code structure (graphify), requirements (dva-kg-mcp), and project artifacts (anchor mcp) with glean fallback.",
        "tags": tags,
        "mcp": mcp_config,
        "auto_detect": auto_detect,
        "context": {
            "project_name": project_name,
            "project_path": str(project_path),
            "domain": domain,
            "product": product,
            "languages": analysis.languages,
            "frameworks": analysis.frameworks,
            "has_graphify": (project_path / "graphify-out" / "graph.json").exists(),
        },
    }

    return skill_config


def generate_project_context_skill_content(
    project_path: Path,
    analysis: ProjectAnalysis,
    domain: str | None = None,
    product: str | None = None,
) -> str:
    """Generate SKILL.md content for the project context skill.

    Args:
        project_path: Path to the project repository
        analysis: Project analysis results
        domain: Optional domain name
        product: Optional product name

    Returns:
        SKILL.md content as string
    """
    project_name = project_path.name
    has_graphify = (project_path / "graphify-out" / "graph.json").exists()

    content = f"""---
description: >-
  Root context skill for {project_name}. Provides unified access to code structure
  (graphify), domain requirements (dva-kg-mcp), and project artifacts (anchor mcp)
  with glean fallback. Use this skill for all code development tasks requiring
  project-specific context.
tags:
  - project-context
  - root-skill
{f"  - domain:{domain}" if domain else ""}
{f"  - product:{product}" if product else ""}
mcp:
  server: multi
  servers:
    - name: graphify
      purpose: code-structure
      description: Query codebase structure and architecture
      fallback: false
    - name: dva-kg-mcp
      purpose: requirements
      description: Access domain requirements and release context
      fallback: false
      params:
        domain: {domain if domain else "null"}
        product: {product if product else "null"}
    - name: anchor
      purpose: project-artifacts
      description: Access Jira, Bitbucket, Confluence
      fallback: false
      params:
        jira: true
        bitbucket: true
        confluence: true
    - name: glean
      purpose: general-knowledge
      description: Fallback for general knowledge
      fallback: true
  fallback_chain:
    - dva-kg-mcp
    - anchor
    - glean
---

# {project_name} Project Context

This is the root context skill for the **{project_name}** project.

## Project Overview

- **Name**: {project_name}
- **Path**: `{project_path}`
- **Languages**: {', '.join(analysis.languages) if analysis.languages else 'None detected'}
- **Frameworks**: {', '.join(analysis.frameworks) if analysis.frameworks else 'None detected'}
{f"- **Domain**: {domain}" if domain else ""}
{f"- **Product**: {product}" if product else ""}
{f"- **Graphify Available**: {'Yes' if has_graphify else 'No'}" if has_graphify else ""}

## Context Sources

This skill provides access to the following context sources in priority order:

### 1. Graphify (Code Structure)
Use for codebase architecture questions:
- "What is the structure of this project?"
- "Show me the dependencies between modules X and Y"
- "Which files use class Z?"

### 2. DVA KG MCP (Requirements & Release Context)
Use for domain-specific requirements:
- "What are the requirements for feature X?"
- "What is in release R29?"
- "What are the business rules for this domain?"

### 3. Anchor MCP (Project Artifacts)
Use for project-specific artifacts:
- Jira issues and tickets
- Bitbucket pull requests and code review
- Confluence documentation

### 4. Glean (Fallback)
Use for general company knowledge when other sources fail.

## Usage

For any code development task, start with this skill to get project context.
The skill will automatically route queries to the appropriate context source
based on the question type and fallback chain.

## When to Use Additional Skills

While this skill provides comprehensive project context, you may still need
additional skills for:
- Language-specific patterns (e.g., `java-spring-boot`, `python-fastapi`)
- Testing frameworks (e.g., `junit`, `pytest`)
- Build tools (e.g., `maven`, `gradle`, `npm`)

These can be added alongside this root context skill.
"""
    return content
