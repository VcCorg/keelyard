"""Prompts and question definitions for AI-powered skill generation."""

# Skill type labels and their descriptions
SKILL_TYPE_LABELS = {
    "capability": "Capability — A specific, reusable function or workflow",
    "framework": "Framework — Language/framework-specific patterns and best practices",
    "domain": "Domain Knowledge — Specialized knowledge for an industry/domain",
    "mcp": "MCP Integration — MCP server or tool wrapper",
    "data": "Data & Integration — Data source, API, or pipeline integration",
}

# Dynamic questions per skill type
# Format: (field_key, prompt_text, is_optional)
QUESTIONS_BY_TYPE = {
    "capability": [
        ("inputs", "What inputs/parameters does this capability take? (e.g., PR URL, code snippet)", False),
        ("outputs", "What does it produce or return?", False),
        ("use_case", "Give a concrete example of when to use this", True),
        ("mcp_servers", "Does it need any MCP servers? (e.g., bitbucket, jira, memory) Leave blank if none", True),
    ],
    "framework": [
        ("framework", "Which framework/language? (e.g., Spring Boot, FastAPI, React)", False),
        ("patterns", "Key patterns or best practices to cover", False),
        ("versions", "Specific versions? (e.g., Spring Boot 3.x, FastAPI 0.100+)", True),
        ("mcp_servers", "Any MCP tools needed? (e.g., confluence for docs) Leave blank if none", True),
    ],
    "domain": [
        ("domain", "What domain/industry? (e.g., Healthcare, Finance, E-Commerce)", False),
        ("concepts", "Key concepts or domain terminology to explain", False),
        ("regulatory", "Are there compliance/regulatory considerations? (e.g., HIPAA, PCI-DSS)", True),
        ("mcp_servers", "Any MCP tools for this domain? Leave blank if none", True),
    ],
    "mcp": [
        ("server_name", "Name of the MCP server or tool (e.g., bitbucket, jira)", False),
        ("capabilities", "What capabilities does it expose? (e.g., search issues, create PRs, run queries)", False),
        ("auth", "Authentication required? (e.g., PAT, API key, OAuth)", True),
        ("endpoints", "Key endpoints or tool names (comma-separated)", True),
    ],
    "data": [
        ("source", "Data source or system (e.g., Postgres, Snowflake, Salesforce, S3)", False),
        ("operations", "What operations does it support? (e.g., query, ingest, transform)", False),
        ("format", "Data format/schema? (e.g., relational, JSON, Parquet)", True),
        ("mcp_servers", "Any MCP servers for this integration? Leave blank if none", True),
    ],
}

SKILL_CREATOR_SYSTEM = """You are an expert AI skill architect specializing in creating Agent Skills in agentskills.io format.

Your role is to generate production-quality SKILL.md files that:
1. Follow strict agentskills.io format with YAML frontmatter + markdown body
2. Are clear, concise, and immediately actionable for AI agents
3. Include concrete examples and step-by-step workflows
4. Reference MCP tools/servers where applicable
5. Use professional, accessible language
6. Are structured for maximum discoverability

Always generate complete, ready-to-use SKILL.md files. Do NOT generate code or implementation — focus on skill definition, workflows, and usage patterns.

Format strictly as:
---
name: skill-name
description: >-
  One-line description
tags: [tag1, tag2, tag3]
---

# Skill Title

## Overview
2-3 sentences about what this skill does

## When to Use This Skill
- Scenario 1
- Scenario 2
- Scenario 3

## Available Tools & MCP Servers
(table if applicable)

## Key Workflows
1. Step one
2. Step two
3. Step three

## Inputs & Configuration
What the skill needs to operate

## Outputs & Results
What the skill produces

## Examples
3-4 concrete, realistic examples

## Best Practices
Tips for effective use

## Prerequisites & Setup
(if applicable)
"""

SKILL_CREATOR_USER = """Generate a production-quality SKILL.md file for this skill:

**Skill Type:** {skill_type}
**Skill Name:** {name}
**One-liner:** {one_liner}

**Details:**
{details}

**Target Environments:** {environments}

Create a complete, ready-to-use SKILL.md file following agentskills.io format.
Focus on clarity, workflows, and examples. Be specific and actionable."""

SKILL_REFINE_USER = """Here's the current skill:

```
{current_skill}
```

User feedback: {feedback}

Please refine the skill based on this feedback. Return the complete updated SKILL.md file.
Maintain the same structure and agentskills.io format."""
