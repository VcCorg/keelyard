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
# Note: These follow Anthropic's Stage 1 (Capture Intent) methodology
QUESTIONS_BY_TYPE = {
    "capability": [
        # Stage 1: Intent Capture (Trigger, Input/Output, Success, Edge cases)
        ("trigger", "When/how should this capability be triggered? (e.g., on PR submission, user command)", False),
        ("inputs", "What inputs/parameters does this capability take? (e.g., PR URL, code snippet)", False),
        ("outputs", "What does it produce or return? Be specific about format", False),
        ("success_criteria", "How do we know this skill succeeded? (metrics, user feedback, validation)", True),
        ("edge_cases", "What edge cases or error conditions should it handle?", True),
        # Stage 2: Additional context
        ("use_case", "Give 1-2 concrete examples of when to use this", True),
        ("mcp_servers", "Does it need any MCP servers? (e.g., bitbucket, jira, memory) Leave blank if none", True),
    ],
    "framework": [
        # Stage 1: Intent Capture
        ("framework", "Which framework/language? (e.g., Spring Boot, FastAPI, React)", False),
        ("use_context", "In what context/workflow would devs use this? (e.g., project setup, debugging, optimization)", False),
        ("patterns", "Key patterns or best practices to cover", False),
        ("success_criteria", "How do we measure if someone successfully applied this skill?", True),
        ("common_mistakes", "What common mistakes should the skill help avoid?", True),
        # Stage 2: Additional context
        ("versions", "Specific versions? (e.g., Spring Boot 3.x, FastAPI 0.100+)", True),
        ("mcp_servers", "Any MCP tools needed? (e.g., confluence for docs) Leave blank if none", True),
    ],
    "domain": [
        # Stage 1: Intent Capture
        ("domain", "What domain/industry? (e.g., Healthcare, Finance, E-Commerce)", False),
        ("use_context", "What problems in this domain should the skill help solve?", False),
        ("concepts", "Key concepts or domain terminology to explain", False),
        ("success_criteria", "What makes a response accurate/helpful in this domain?", True),
        ("regulatory", "Are there compliance/regulatory considerations? (e.g., HIPAA, PCI-DSS)", True),
        # Stage 2: Additional context
        ("mcp_servers", "Any MCP tools for this domain? Leave blank if none", True),
    ],
    "mcp": [
        # Stage 1: Intent Capture
        ("server_name", "Name of the MCP server or tool (e.g., bitbucket, jira)", False),
        ("use_context", "What user workflows does this MCP server enable?", False),
        ("capabilities", "What capabilities does it expose? (e.g., search issues, create PRs, run queries)", False),
        ("required_config", "What configuration/setup is required to use this?", True),
        ("auth", "Authentication required? (e.g., PAT, API key, OAuth)", True),
        # Stage 2: Additional context
        ("endpoints", "Key endpoints or tool names (comma-separated)", True),
    ],
    "data": [
        # Stage 1: Intent Capture
        ("source", "Data source or system (e.g., Postgres, Snowflake, Salesforce, S3)", False),
        ("use_context", "What data tasks/workflows does this skill enable?", False),
        ("operations", "What operations does it support? (e.g., query, ingest, transform)", False),
        ("security_considerations", "Any security/privacy considerations? (PII, encryption, access control)", True),
        # Stage 2: Additional context
        ("format", "Data format/schema? (e.g., relational, JSON, Parquet)", True),
        ("mcp_servers", "Any MCP servers for this integration? Leave blank if none", True),
    ],
}

SKILL_CREATOR_SYSTEM = """You are an expert AI skill architect specializing in creating Agent Skills in agentskills.io format.

Your role is to generate production-quality SKILL.md files that follow Anthropic's skill-creator methodology:

**Stage 1 (Capture Intent):** Use the provided trigger conditions, input/output specs, and success criteria
to ensure the skill is discoverable and actionable.

**Stage 2 (Interview):** The user has answered detailed questions about context, workflows, and requirements.

**Stage 3 (Draft):** Generate the SKILL.md with clear workflows, examples, and best practices.

Your skill files should:
1. Follow strict agentskills.io format with YAML frontmatter + markdown body
2. Be clear, concise, and immediately actionable for AI agents
3. Include concrete examples and step-by-step workflows
4. Reference MCP tools/servers where applicable
5. Use professional, accessible language
6. Be structured for maximum discoverability

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
2-3 sentences about what this skill does, including when to trigger it.

## When to Use This Skill
- Scenario 1
- Scenario 2
- Scenario 3

## Trigger & Activation
When/how this skill should be invoked. Be specific about triggering conditions.

## Inputs & Configuration
What the skill needs to operate (parameters, format, configuration)

## Outputs & Results
What the skill produces (output format, structure, examples)

## Success Criteria
How to measure if this skill worked correctly.

## Key Workflows
1. Step one
2. Step two
3. Step three

## Examples
3-4 concrete, realistic examples with inputs and expected outputs.

## Best Practices
Tips for effective use and common pitfalls to avoid.

## Edge Cases & Error Handling
Known edge cases and how the skill should handle them.

## Available Tools & MCP Servers
(table if applicable)

## Prerequisites & Setup
(if applicable)
"""

SKILL_CREATOR_USER = """Generate a production-quality SKILL.md file for this skill:

**Skill Type:** {skill_type}
**Skill Name:** {name}
**One-liner:** {one_liner}

**Collected Requirements (Stage 1 Intent Capture):**
{details}

**Target Environments:** {environments}

Create a complete, ready-to-use SKILL.md file following agentskills.io format.

CRITICAL:
- Include the "Trigger & Activation" section with specific conditions for when this skill should be used
- Clearly specify input parameters, their format, and required values
- Document exact output format with examples
- Add a "Success Criteria" section explaining how users know the skill worked
- Include an "Edge Cases & Error Handling" section
- Provide 3-4 concrete examples with specific inputs and expected outputs
- Be actionable and specific — avoid generic guidance

Focus on Stage 1 intent capture by making the skill's purpose, trigger conditions, and success criteria crystal clear."""

SKILL_REFINE_USER = """Here's the current skill:

```
{current_skill}
```

User feedback: {feedback}

Please refine the skill based on this feedback. Return the complete updated SKILL.md file.
Maintain the same structure and agentskills.io format."""
