---
name: jira
description: >-
  Fetch and manage Jira issues, sprints, and transitions via MCP.
  Use this skill when the user asks about Jira tickets, sprint work,
  or needs to look up acceptance criteria before starting development.
mcp_server: jira
---

# Jira Integration

You have access to a Jira MCP server. Use these tools to interact with Jira Server.

## Available Tools

| Tool | Purpose | Key Args |
|------|---------|----------|
| `get_issue` | Fetch issue details by key | `issue_key` (e.g., CGP-1234) |
| `search_issues` | JQL search | `jql`, `max_results` |
| `get_my_issues` | Current user's assigned issues | — |
| `get_comments` | Issue comments | `issue_key` |
| `add_comment` | Post a comment | `issue_key`, `body` |
| `get_transitions` | Available status transitions | `issue_key` |
| `transition_issue` | Move issue to new status | `issue_key`, `transition_id` |
| `assign_issue` | Assign issue to user | `issue_key`, `assignee` |
| `list_projects` | List all Jira projects | — |
| `get_sprint_issues` | Issues in active sprint | `board_id` |

## When to Use

- User mentions a Jira ticket key (e.g., "look at CGP-1234", "what's in IMTO-3008")
- User asks about sprint work, backlog, or assigned issues
- User needs acceptance criteria or requirements before starting development
- User wants to update a ticket status after completing work
- User asks "what should I work on next"

## Common Workflows

### Get context before coding
1. Use `get_issue` to fetch the ticket details
2. Read the description and acceptance criteria
3. Use `get_comments` to see discussion history
4. Summarize requirements for the user

### Find work to do
1. Use `get_my_issues` to list assigned issues
2. Or use `search_issues` with JQL: `assignee = currentUser() AND status != Done ORDER BY priority DESC`
3. Present issues sorted by priority

### Update ticket after work
1. Use `get_transitions` to see available status moves
2. Use `transition_issue` to move to "In Progress", "In Review", or "Done"
3. Use `add_comment` to note what was done

## JQL Examples

- Open issues assigned to me: `assignee = currentUser() AND status != Done`
- High priority bugs: `type = Bug AND priority in (Critical, Blocker) AND status != Done`
- Sprint work: `sprint in openSprints()`
- Recently updated: `project = CGP AND updated >= -7d ORDER BY updated DESC`
