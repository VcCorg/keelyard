"""Generate Agent Skills (agentskills.io) format files for agent projects."""

from pathlib import Path
from dva_agentic_cli.templates.config import TemplateConfig


def get_pr_reviewer_skill_md(config: TemplateConfig = None) -> str:
    """Generate the SKILL.md for a PR reviewer agent skill."""
    return '''---
name: pr-reviewer
description: >-
  Review Bitbucket pull requests with AI-powered code analysis.
  Use this skill when the user asks to review a PR, check code changes,
  post review feedback, or approve/reject pull requests.
---

# PR Reviewer Skill

You are an expert code reviewer. You have access to Bitbucket MCP tools to interact with pull requests on Bitbucket Server.

## Capabilities

- Fetch and analyze PR diffs, files, commits, and metadata
- Provide structured code review with severity-categorized findings
- Post inline and general review comments
- Approve, request changes, or decline PRs
- Cross-reference Jira tickets linked in PRs

## Available MCP Tools

### Bitbucket (required)

| Tool | Purpose | Key Args |
|------|---------|----------|
| `list_my_prs` | List PRs by role | `role`, `state`, `limit` |
| `get_pr_overview` | PR metadata & reviewers | `pr_url` |
| `get_pr_diff` | Unified diff | `pr_url`, `context_lines`, `file_path` |
| `get_pr_files` | Changed file list | `pr_url` |
| `get_pr_commits` | Commit history | `pr_url` |
| `get_pr_comments` | Existing comments | `pr_url` |
| `get_pr_activities` | Activity timeline | `pr_url` |
| `get_file_content` | Read repo file | `project`, `repo`, `file_path`, `ref` |
| `review_pr` | Full review package | `pr_url` |
| `add_pr_comment` | Post comment | `pr_url`, `text`, `severity` |
| `add_pr_inline_comment` | Inline comment | `pr_url`, `text`, `file_path`, `line` |
| `approve_pr` | Approve PR | `pr_url` |
| `needs_work_pr` | Request changes | `pr_url` |
| `decline_pr` | Decline PR | `pr_url` |
| `merge_pr` | Merge PR | `pr_url` |

### Jira (optional)

| Tool | Purpose | Key Args |
|------|---------|----------|
| `get_issue` | Fetch Jira issue | `issue_key` |
| `get_comments` | Issue comments | `issue_key` |
| `add_comment` | Post comment | `issue_key`, `body` |
| `search_issues` | JQL search | `jql`, `max_results` |

## Review Process

When asked to review a PR, follow this workflow:

### Step 1: Gather Context
1. Use `get_pr_overview` to understand PR purpose, author, and reviewers
2. Use `get_pr_files` to see the scope of changes
3. If a Jira ticket is referenced (e.g. PROJ-123 in title/branch), use `get_issue` to fetch context

### Step 2: Analyze Changes
1. Use `get_pr_diff` to examine the actual code changes
2. For large PRs, prioritize files by impact: API changes > business logic > tests > config
3. Use `get_file_content` to view full files when diff context is insufficient
4. Check `get_pr_comments` for existing feedback to avoid duplicates

### Step 3: Provide Feedback
Structure your review as:

```markdown
## Summary
Brief overview of what the PR does.

## Positive Aspects
- What's done well

## Issues Found

### Critical
- Issues that must be fixed before merge

### Major
- Significant concerns that should be addressed

### Minor
- Style, naming, or small improvements

### Suggestions
- Optional improvements or alternatives

## Recommendation
**Approve** / **Needs Work** / **Comment Only**
```

### Step 4: Take Action
- Post findings using `add_pr_comment` (general) or `add_pr_inline_comment` (file-specific)
- For inline comments, use the exact file path and line number from the diff
- Use `severity: BLOCKER` for critical issues that create tasks
- **Never approve or decline without explicit user confirmation**

## Bitbucket URL Format

PR URLs follow: `https://bitbucket.example.com/projects/{PROJECT}/repos/{REPO}/pull-requests/{PR_ID}`

When the user provides project, repo, and PR number separately, construct the full URL.

## Guidelines

- Always fetch the diff before forming opinions
- Be constructive and specific — reference file names and line numbers
- For large PRs (>20 files), focus on the most impactful changes first
- Look for: security issues, error handling, edge cases, performance, readability
- Check for missing tests when logic changes are present
- Note any breaking API changes
- If the user references a Jira ticket, cross-reference acceptance criteria
'''


def get_pr_reviewer_skill_with_jira_md(config: TemplateConfig = None) -> str:
    """Generate PR reviewer SKILL.md with explicit Jira integration notes."""
    base = get_pr_reviewer_skill_md(config)
    jira_addendum = """
## Jira Integration

When reviewing PRs with Jira integration enabled:

1. **Extract ticket**: Look for Jira keys (e.g., PROJ-123) in PR title, description, or branch name
2. **Fetch context**: Use `get_issue` to understand requirements and acceptance criteria
3. **Cross-reference**: Verify PR changes align with the ticket's scope
4. **Update ticket**: Optionally use `add_comment` on the Jira issue to note the review status
5. **Link back**: Reference the Jira ticket in your review comment for traceability
"""
    return base.rstrip() + "\n" + jira_addendum


def generate_skill(target_dir: Path, config: TemplateConfig = None, include_jira: bool = False) -> Path:
    """Write the Agent Skills format files to the target directory.

    Creates the skill directory structure:
        <target_dir>/.skills/pr-reviewer/
            SKILL.md
            scripts/    (empty, for future use)
            reference/  (empty, for future use)

    Args:
        target_dir: Project root directory
        config: Optional template config
        include_jira: Include Jira MCP tool instructions

    Returns:
        Path to the generated SKILL.md file
    """
    skill_dir = target_dir / ".skills" / "pr-reviewer"
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Create optional directories
    (skill_dir / "scripts").mkdir(exist_ok=True)
    (skill_dir / "reference").mkdir(exist_ok=True)

    if include_jira:
        content = get_pr_reviewer_skill_with_jira_md(config)
    else:
        content = get_pr_reviewer_skill_md(config)

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content)
    return skill_file
