"""Default prompt templates for the onboard agent.

These can be overridden by:
1. Passing custom prompts dict to pipeline functions
2. Loading from external markdown files in a standalone agent project
3. Subclassing and replacing in a custom agent

Override keys: "gap_detection", "skill_content", "skill_enrichment"
"""

from pathlib import Path
from typing import Optional


GAP_DETECTION = """You are an expert software engineering assistant that helps developers get the right coding skills for AI code assistants.

## Context

A project has been analyzed with the following tech stack:

**Languages:** {languages}
**Frameworks:** {frameworks}
**Build Tools:** {build_tools}
**Test Frameworks:** {test_frameworks}
**Databases:** {databases}
**API Types:** {api_types}
**CI/CD:** {ci_cd}
**Docker:** {has_docker}
**Dependencies ({dep_count}):**
{top_dependencies}

**Source patterns detected:** {source_patterns}

## Currently Installed Skills

These skills have already been matched and installed from the registry:
{installed_skills}

## Available Skills in Registry (not installed)

These skills exist in the registry but were NOT matched:
{available_skills}

## Your Task

Analyze this project and identify **skill gaps** — technologies, patterns, or frameworks used by this project that are NOT covered by any existing skill in the registry (neither installed nor available).

For each gap, provide:
1. **skill_name**: A kebab-case name for the proposed skill (e.g., "spring-cloud-gcp", "spanner-change-streams")
2. **description**: One-line description of what the skill covers
3. **tags**: List of relevant tags
4. **reason**: Why this skill is needed (what in the project uses it)
5. **auto_detect**: Detection rules for the registry entry:
   - "files": list of files whose presence indicates this skill
   - "dependencies": list of dependency patterns (any match triggers)
   - "dependencies_all": list of dependencies that ALL must be present
   - "source_patterns": list of code patterns to look for

Only propose skills that represent **substantial** technology areas (not individual libraries). A skill should cover a framework, platform, pattern, or tool that an AI assistant needs specific knowledge about.

Return a JSON array of skill gap objects. If no gaps are found, return an empty array [].
Return ONLY the JSON array, no other text.
"""

SKILL_CONTENT = """You are an expert developer creating a coding skill reference for AI code assistants.

Generate a SKILL.md file for the following technology:

**Skill Name:** {skill_name}
**Description:** {description}
**Tags:** {tags}
**Reason it was detected:** {reason}

The skill file should follow this exact format:

```
---
name: {skill_name}
description: >-
  {description}
  Use this skill when working with {skill_name} technologies.
---

# [Title]

## Key Concepts
[Core concepts, 3-5 bullet points]

## Project Conventions
[Package structure, file layout, naming conventions]

## Common Patterns
[Code examples showing idiomatic usage — use fenced code blocks]

## Guidelines
[Best practices, 5-8 bullet points]
```

Generate comprehensive, practical content that an AI coding assistant would use to give better suggestions.
Focus on patterns, conventions, and best practices — NOT tutorials.
Return ONLY the SKILL.md content, no wrapping text.
"""

SKILL_ENRICHMENT = """You are an expert developer enhancing a coding skill with project-specific context.

## Current Skill Content
```
{current_content}
```

## Project Analysis
**Languages:** {languages}
**Frameworks:** {frameworks}
**Dependencies:** {dependencies}

## Detected Patterns in This Project
{source_patterns}

## Task

Add a "## Project-Specific Notes" section at the end of the skill with:
1. Specific conventions observed in this project
2. Key dependencies and their versions
3. Any patterns that differ from the generic skill guidance

Keep additions concise (10-15 lines max). Do NOT modify the existing content.
Return the COMPLETE updated SKILL.md content.
"""

# Default prompt registry — keyed so standalone agents can override selectively
DEFAULTS = {
    "gap_detection": GAP_DETECTION,
    "skill_content": SKILL_CONTENT,
    "skill_enrichment": SKILL_ENRICHMENT,
}


def load_prompts_from_dir(prompts_dir: Path) -> dict[str, str]:
    """Load prompt overrides from a directory of markdown files.

    Files are named after the prompt key: gap_detection.md, skill_content.md, etc.
    Only files that exist override the defaults.

    Args:
        prompts_dir: Directory containing .md prompt files.

    Returns:
        Merged dict of default + overridden prompts.
    """
    prompts = dict(DEFAULTS)
    if not prompts_dir.is_dir():
        return prompts

    for key in DEFAULTS:
        md_file = prompts_dir / f"{key}.md"
        if md_file.exists():
            prompts[key] = md_file.read_text()

    return prompts


def get_prompts(overrides: Optional[dict[str, str]] = None) -> dict[str, str]:
    """Get prompt templates with optional overrides.

    Args:
        overrides: Dict of prompt key -> template string to override defaults.

    Returns:
        Complete prompt dict.
    """
    prompts = dict(DEFAULTS)
    if overrides:
        prompts.update(overrides)
    return prompts
