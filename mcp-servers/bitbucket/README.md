# Bitbucket Server MCP

An MCP (Model Context Protocol) server that exposes Bitbucket Server/Data Center pull request data to AI assistants like Windsurf Cascade.

## Why?

Bitbucket Server sits behind corporate auth. AI assistants can't access PR URLs directly. This MCP server bridges the gap — giving Cascade full access to PR diffs, comments, commits, and metadata via authenticated API calls.

## Tools

| Tool | Description |
|------|-------------|
| `get_pr_overview` | PR title, description, author, reviewers, status, merge readiness |
| `get_pr_diff` | Full unified diff (with optional file filter) |
| `get_pr_files` | List of changed files with change types |
| `get_pr_commits` | Commit history in the PR |
| `get_pr_comments` | Existing review comments (including inline) |
| `get_pr_activities` | Full activity timeline (comments, approvals, rescopes) |
| `get_file_content` | Read any file from the repository |
| `review_pr` | All-in-one: overview + files + diff + commits + comments |

All PR tools accept either a full `pr_url` or `project` + `repo` + `pr_id` separately.

## Setup

### 1. Generate a Personal Access Token

1. Go to your Bitbucket Server → Profile → **Manage Account** → **Personal Access Tokens**
2. Create a token with **Read** permissions on projects/repos
3. Copy the token

### 2. Install

```bash
cd bitbucket-server-mcp
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env with your token and server URL
```

Or set environment variables:

```bash
export BITBUCKET_SERVER_URL=https://bitbucket.example.com
export BITBUCKET_PERSONAL_ACCESS_TOKEN=your-token-here
```

### 4. Register with Windsurf

Add to `.windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "bitbucket": {
      "command": "python",
      "args": ["-m", "bitbucket_server_mcp.server"],
      "env": {
        "BITBUCKET_SERVER_URL": "https://bitbucket.example.com",
        "BITBUCKET_PERSONAL_ACCESS_TOKEN": "${BITBUCKET_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
```

Or use the agent CLI:

```bash
`agent mcp add bitbucket --type stdio \
  --command python \
  --args "-m bitbucket_server_mcp.server"
`agent mcp sync --ide windsurf
```

## Usage in Windsurf

Once configured, ask Cascade:

- *"Review PR https://bitbucket.example.com/projects/CGP/repos/cwow-patient-query-spanner/pull-requests/1936"*
- *"Show me the diff for PR 1936 in CGP/cwow-patient-query-spanner"*
- *"What files changed in this PR?"*
- *"Are there any review comments on this PR?"*

## Development

```bash
# Run tests
pytest -v

# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/
```

## Architecture

```
bitbucket-server-mcp/
├── src/bitbucket_server_mcp/
│   ├── __init__.py
│   ├── config.py            # Pydantic settings (env vars)
│   ├── bitbucket_client.py  # Bitbucket Server REST API client
│   └── server.py            # MCP server (stdio transport, FastMCP)
├── tests/
│   └── test_bitbucket_client.py
├── pyproject.toml
├── .env.example
└── README.md
```

- **Transport:** stdio (Windsurf launches the process directly)
- **API:** Bitbucket Server REST API 1.0
- **Auth:** Personal Access Token via Bearer header
- **SDK:** `mcp` Python SDK with `FastMCP` helper
