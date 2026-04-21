---
name: bitbucket
description: >-
  Bitbucket PR operations, code review, and file browsing via MCP.
  Use this skill when the user asks about pull requests, code changes,
  or needs to interact with Bitbucket Server repositories.
mcp_server: bitbucket
---

# Bitbucket Integration

You have access to a Bitbucket MCP server. Use these tools to interact with Bitbucket Server.

## Available Tools

| Tool | Purpose | Key Args |
|------|---------|----------|
| `list_my_prs` | List PRs by role | `role` (reviewer/author), `state`, `limit` |
| `get_pr_overview` | PR metadata & reviewers | `pr_url` or `project`+`repo`+`pr_id` |
| `get_pr_diff` | Unified diff | `pr_url`, `context_lines`, `file_path` |
| `get_pr_files` | Changed file list | `pr_url` |
| `get_pr_commits` | Commit history | `pr_url` |
| `get_pr_comments` | Existing review comments | `pr_url` |
| `get_pr_activities` | Activity timeline | `pr_url` |
| `get_file_content` | Read a repo file | `project`, `repo`, `file_path`, `ref` |
| `review_pr` | Full review package | `pr_url` |
| `add_pr_comment` | Post general comment | `pr_url`, `text`, `severity` |
| `add_pr_inline_comment` | Post inline comment | `pr_url`, `text`, `file_path`, `line` |

## URL Format

PR URLs follow: `https://bitbucket.example.com/projects/{PROJECT}/repos/{REPO}/pull-requests/{PR_ID}`

When the user provides project, repo, and PR number separately, construct the full URL.

## When to Use

- User asks about a pull request (review, diff, comments, status)
- User wants to see what PRs are assigned to them
- User needs to read a file from a Bitbucket repository
- User wants to post review feedback

## Common Workflows

### Check my PRs
1. Use `list_my_prs` with `role=reviewer` to see PRs awaiting review
2. Use `list_my_prs` with `role=author` to see own PRs

### Read a file from repo
1. Use `get_file_content` with `project`, `repo`, `file_path`
2. Optionally specify `ref` for a branch or commit
