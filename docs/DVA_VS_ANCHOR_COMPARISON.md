# DVA vs Anchor MCP — Implementation Comparison

Deep technical comparison between our **DVA Agentic Platform** and the Framework Team's **Anchor MCP Server**.

**Source:** [Anchor MCP Server — Confluence FWT Space](https://confluence.example.com/spaces/FWT/pages/1170481276/Anchor+MCP+Server)

---

## 1. Architecture Philosophy

### Anchor MCP (Framework Team)

**Monolith — one server, all integrations bundled.**

```
┌─────────────────────────────────────────────┐
│           Anchor MCP Server (Node.js)       │
│  ┌─────┐ ┌──────┐ ┌──────────┐ ┌─────┐    │
│  │Jira │ │Bitbkt│ │Confluence│ │Figma│    │
│  └──┬──┘ └──┬───┘ └────┬─────┘ └──┬──┘    │
│     └────────┴──────────┴──────────┘        │
│           Transport Layer (Express/SSE)      │
│           Prompt Handlers (orchestrators)    │
└──────────────────────┬──────────────────────┘
                       │ :3000/mcp
                    AI Client
```

- Single `index.cjs` / `index-server.js` entry point
- All tool handlers, prompt handlers, and service clients in one process
- Built on official MCP SDK for Node.js (`@modelcontextprotocol/sdk`)
- Express server for remote SSE mode
- Single Docker container (or local stdio process)

### DVA Agentic Platform (Ours)

**Microservices — one server per integration, independently deployable.**

```
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│Bitbucket │ │  Jira    │ │Confluence│ │  Glean   │ │ Memory   │ │   KG     │
│ :8126    │ │  :8128   │ │  :8129   │ │  :8127   │ │  :8130   │ │  :8131   │
└────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
     └──────┬─────┴──────┬─────┴──────┬──────┴──────┬─────┴──────┬─────┘
            │         dva-network (Docker)           │
     ┌──────┴────────────────────────────────────────┴──────┐
     │            MCP Gateway :9090 (optional)              │
     │     Discovers tools dynamically, namespaces them     │
     └──────────────────────┬───────────────────────────────┘
                            │
                         AI Client
```

- Each service is an independent Python package with its own `pyproject.toml`, `Dockerfile`, `src/` layout
- All share a common pattern: `config.py` (pydantic-settings) → `<name>_client.py` (httpx) → `server.py` (FastMCP)
- Docker Compose orchestrates all services on a shared network
- Gateway optionally aggregates all tools behind a single endpoint
- CLI (`dva mcp`) manages lifecycle, health, and IDE config sync

---

## 2. Language & SDK

| Aspect | Anchor | DVA |
|--------|--------|-----|
| **Language** | Node.js / JavaScript | Python 3.12 |
| **MCP SDK** | `@modelcontextprotocol/sdk` (official JS SDK) | `mcp` package + `FastMCP` (official Python SDK) |
| **HTTP Client** | Built-in `fetch` / `node:http` | `httpx` (sync + async) |
| **Config Management** | Environment variables (raw `process.env`) | `pydantic-settings` (typed, validated, `.env` auto-load) |
| **Build System** | `npm run build` → CommonJS bundle | `hatchling` → wheel per service |
| **Container Base** | Node.js image (likely `node:18-slim`) | `python:3.12-slim` (all services) |

**Impact:** Our pydantic-settings approach catches config errors at startup with typed validation. Anchor relies on runtime checks. Both are valid — Anchor is simpler, ours is more defensive.

---

## 3. Transport & Deployment

| Aspect | Anchor | DVA |
|--------|--------|-----|
| **Local mode** | stdio (`node index-stdio.js`) | stdio (`python -m <pkg>.server`) |
| **Remote mode** | Express/SSE (`node index-server.js`, port 3000) | FastMCP SSE (one port per service) |
| **SSE endpoint** | `/mcp` (single path) | `/sse` (per service) |
| **Docker** | Single container | 8 containers (Docker Compose) |
| **Health checks** | Not documented | `curl --max-time 2` per container, exit-code 28 trick for SSE |
| **Scaling** | Scale the one container | Scale individual services independently |
| **Network** | Standalone | Shared `dva-network` (external Docker network) |

**Key difference:** Anchor is operationally simpler — one container, one port. DVA allows independent scaling and failure isolation (e.g., if Glean goes down, Jira stays up). The gateway provides the "single endpoint" option when wanted.

---

## 4. Tool Coverage Comparison

### 4a. Jira

| Tool | Anchor | DVA |
|------|--------|-----|
| Get issue details | `jira_get_issue` | `get_issue` |
| JQL search | `jira_search_issues` | `search_issues` |
| Get comments | `jira_get_issue_comments` | `get_comments` |
| Get remote links (Confluence, Figma) | `jira_get_remote_links` | ❌ |
| Get project metadata | `jira_get_project` | `list_projects` |
| Get my issues | ❌ | `get_my_issues` |
| Add comment | ❌ | `add_comment` ✏️ |
| Get transitions | ❌ | `get_transitions` |
| Transition issue (change status) | ❌ | `transition_issue` ✏️ |
| Assign issue | ❌ | `assign_issue` ✏️ |
| Sprint issues | ❌ | `get_sprint_issues` |
| Config diagnostic | ❌ | `get_jira_config` |

**Analysis:** Anchor is **read-only** by design (security choice). DVA has **write operations** (add comment, transition, assign) — more powerful but higher risk surface. DVA has 11 tools vs Anchor's 5. Anchor's `jira_get_remote_links` is unique — it follows links to Confluence/Figma automatically.

### 4b. Bitbucket

| Tool | Anchor | DVA |
|------|--------|-----|
| Get file content | `get_file_content` | `get_file_content` |
| Get PR diff | `get_pull_request_diff` | `get_pr_diff` |
| Search code | `search_code` | ❌ |
| List branches | `list_branches` | ❌ |
| Get commits | `get_commits` | `get_pr_commits` |
| List folder contents | `list_folder_contents` | ❌ |
| Search PRs | `search_pull_requests` | ❌ |
| Get PR comments | `get_pull_request_comments` | `get_pr_comments` |
| Get PR overview | ❌ | `get_pr_overview` |
| Get PR files (change list) | ❌ | `get_pr_files` |
| Get PR activities | ❌ | `get_pr_activities` |
| Review package (all-in-one) | ❌ | `review_pr` |
| List my PRs (dashboard) | ❌ | `list_my_prs` |
| Add PR comment | ❌ | `add_pr_comment` ✏️ |
| Add inline comment | ❌ | `add_pr_inline_comment` ✏️ |
| Approve/unapprove PR | ❌ | `approve_pr`, `unapprove_pr` ✏️ |
| Needs work / decline | ❌ | `needs_work_pr`, `decline_pr` ✏️ |
| Merge PR | ❌ | `merge_pr` ✏️ |

**Analysis:** Anchor has **repo-level tools** (browse code, list branches, search code across repos). DVA is **PR-focused** (deep review, inline comments, approve/merge, status changes). Anchor is read-only. DVA has full PR lifecycle write operations. Different design intents — Anchor for browsing, DVA for automated code review.

### 4c. Confluence

| Tool | Anchor | DVA |
|------|--------|-----|
| Search pages | `confluence_search_pages` | `search_confluence` |
| Get page content | `confluence_get_page` | `get_confluence_page` |
| Get child pages | `confluence_get_page_children` | `get_child_pages` |
| Get attachments | `confluence_get_attachment` | ❌ |
| CQL search (raw) | ❌ | `search_confluence_cql` |
| List spaces | ❌ | `list_confluence_spaces` |
| Get space details | ❌ | `get_confluence_space` |
| Get space pages | ❌ | `get_space_pages` |
| Get page comments | ❌ | `get_page_comments` |
| Add page comment | ❌ | `add_confluence_comment` ✏️ |
| Get page labels | ❌ | `get_page_labels` |

**Analysis:** Anchor has the unique `confluence_get_attachment` (can fetch base64 images from pages). DVA has broader coverage with 10 tools including CQL, space management, comments, and labels. Both use Confluence REST API.

### 4d. Unique to Each

| Anchor Only | DVA Only |
|-------------|----------|
| **Figma** (7 tools): design context, node images, design tokens, component hierarchy, comments, screen specs | **Glean** (6 tools): enterprise search, docs, datasources, agents, chat |
| **Prompt workflows** (4 built-in): analyze-jira-story, implementation-plan, gather-full-context, analyze-development-status | **Memory** (16 tools): short-term, long-term, reasoning traces via Neo4j |
| | **Knowledge Graph** (8 tools): semantic search, entity details, Cypher queries, source management via Neo4j + LightRAG |
| | **Gateway** (dynamic): aggregates all tools behind single endpoint |
| | **CLI management** (`dva mcp`): health, sync, lifecycle |

---

## 5. MCP Prompts vs Agent Skills

This is the biggest **philosophical difference**.

### Anchor: Server-Side Prompt Workflows

Anchor implements MCP **prompts** — pre-defined multi-step recipes that live inside the server:

```
"analyze-jira-story" prompt:
  1. Fetch Jira issue details
  2. Follow remote links → fetch Confluence pages
  3. Follow Figma links → extract design context
  4. Return structured analysis
```

The AI client calls one prompt and gets a complete, orchestrated result. The server does the orchestration.

### DVA: Client-Side Agent Skills

DVA implements **Agent Skills** (agentskills.io standard) — portable markdown files that teach the AI client how to orchestrate tools itself:

```
.skills/pr-reviewer/SKILL.md:
  "When reviewing a PR:
   1. Call get_pr_overview to understand scope
   2. Call get_pr_diff for code changes
   3. Call get_pr_comments for existing feedback
   4. Use search_issues to find the related Jira ticket
   ..."
```

The AI client reads the skill and decides how to chain tool calls. The server just provides atomic tools.

| Aspect | Anchor (Prompts) | DVA (Skills) |
|--------|-----------------|--------------|
| **Orchestration** | Server-side (deterministic) | Client-side (AI decides) |
| **Portability** | Locked to this MCP server | Works with any MCP-compatible tools |
| **Flexibility** | Fixed recipes, update server to change | Edit a markdown file to change |
| **Token efficiency** | One round-trip, server batches API calls | Multiple tool calls, more round-trips |
| **Debugging** | Black box from client perspective | Transparent — AI shows its reasoning |
| **Cross-server** | Can't orchestrate across different MCP servers | Can chain tools from any MCP server |

---

## 6. Code Structure Comparison

### Anchor (estimated from docs)

```
anchor-mcp/
  src/
    index.cjs              ← Single entry point
    tool-handlers/
      jira.js              ← All Jira tools
      bitbucket.js         ← All Bitbucket tools
      confluence.js        ← All Confluence tools
      figma.js             ← All Figma tools
    prompt-handlers/
      analyze-story.js     ← Multi-tool orchestration
      implementation.js
      full-context.js
      dev-status.js
    services/
      jira-service.js      ← REST API client
      bitbucket-service.js
      confluence-service.js
      figma-service.js
    index-server.js        ← Express SSE server
    index-stdio.js         ← stdio transport
  package.json
  Dockerfile
```

**~1 repo, ~1 package, ~1 Dockerfile.**

### DVA (actual)

```
dva-mcp-servers/                           ← 4,391 lines Python
  bitbucket/                               ← 1,423 lines, 6 files
    src/bitbucket_server_mcp/
      config.py                            ← BitbucketConfig (pydantic-settings)
      bitbucket_client.py                  ← BitbucketClient (httpx, context manager)
      server.py                            ← 15 @mcp.tool() functions + 1 @mcp.resource()
    tests/test_bitbucket_client.py         ← 21 tests
    pyproject.toml, Dockerfile
  jira/                                    ← 709 lines, 5 files
    src/jira_server_mcp/
      config.py, jira_client.py, server.py ← 11 tools
    pyproject.toml, Dockerfile
  confluence/                              ← 655 lines, 4 files
    src/confluence_mcp/
      config.py, confluence_client.py, server.py ← 10 tools
    pyproject.toml, Dockerfile
  glean/                                   ← 362 lines, 4 files (async httpx)
  kg/                                      ← 979 lines, 6 files (Neo4j + LightRAG)
  gateway/                                 ← 263 lines, 3 files (dynamic discovery)
  memory/                                  ← Dockerfile only (wraps neo4j-agent-memory[mcp])
  proxy/                                   ← Dockerfile only (wraps mcp-proxy package)
  docker-compose.yml                       ← 8 services orchestrated
```

**8 packages, 8 Dockerfiles, shared Docker Compose.**

---

## 7. Detailed Design Pattern Differences

### 7a. Client Instantiation

**Anchor:** Likely creates API clients at module load and reuses them (single process):
```javascript
// Pseudo-code (inferred)
const jiraClient = new JiraService(process.env.JIRA_BASE_URL, process.env.JIRA_API_TOKEN);
```

**DVA:** Creates a fresh client per tool call using context managers:
```python
# Actual code from server.py
def _get_client() -> BitbucketClient:
    config = BitbucketConfig()       # pydantic-settings, reads env
    return BitbucketClient(config)   # httpx.Client with auth headers

@mcp.tool()
def get_pr_overview(...) -> str:
    with _get_client() as client:    # Fresh client, auto-closes
        overview = client.get_pr(proj, rp, pid)
```

DVA's pattern is more defensive (no stale connections) but creates more HTTP client instances. Anchor's is more efficient for high-throughput but risks stale state.

### 7b. Input Flexibility

**Anchor:** Tools accept specific parameters (issue key, PR URL components).

**DVA:** Tools accept **either** a full URL or component parts, with URL parsing built in:
```python
@mcp.tool()
def get_pr_overview(
    pr_url: str | None = None,      # "https://bitbucket.example.com/projects/CGP/repos/my-repo/pull-requests/123"
    project: str | None = None,      # "CGP"
    repo: str | None = None,         # "my-repo"
    pr_id: int | None = None,        # 123
) -> str:
    proj, rp, pid = _resolve_pr(project, repo, pr_id, pr_url)
```

This means the AI can paste a URL directly from a Jira ticket or chat message and it just works.

### 7c. Write Safety

**Anchor:** Explicitly **read-only** — a design choice for security. From their docs: *"read-only tools ensuring security without modification risks."*

**DVA:** Includes **write operations** marked with ✏️ above:
- PR: approve, unapprove, needs_work, decline, merge, add comments (inline + general)
- Jira: add comment, transition issue, assign issue
- Confluence: add page comment

This is a conscious trade-off. DVA enables automated workflows (e.g., a PR reviewer agent that can approve and add comments). Anchor requires a human to perform those actions.

### 7d. Error Handling

**Anchor:** From their docs — *"Intelligent limitations handling for Sketch links and rate limits."* Tools gracefully handle missing integrations: *"if credentials are not set, those specific tools will simply return an error when called but won't prevent the server from running."*

**DVA:** Each service is independent, so a misconfigured Jira MCP doesn't affect Bitbucket MCP. The `_get_client()` pattern throws a clear `ValueError` if not configured:
```python
if not config.is_configured:
    raise ValueError("Bitbucket Server is not configured. Set BITBUCKET_SERVER_URL and ...")
```

### 7e. Aggregation

**Anchor:** Built-in — it IS the aggregation. One server, all tools.

**DVA:** Two options:
1. **Direct connections** — AI client connects to each service individually (default)
2. **Gateway** — Dynamic tool discovery + namespacing. Connects to upstreams at startup, registers `bitbucket_get_pr_overview`, `jira_get_issue`, etc. Supports `gateway_refresh` for live re-discovery.

---

## 8. What Each Platform Has That the Other Doesn't

### Anchor has, we don't:
1. **Figma integration** (7 tools) — design-to-code bridge, design token extraction
2. **MCP Prompt workflows** — server-side orchestration recipes
3. **Link-following** — `jira_get_remote_links` auto-traverses to Confluence/Figma
4. **Code search** — `search_code` across Bitbucket repos (not just PRs)
5. **Branch listing** — `list_branches` for repo exploration

### We have, Anchor doesn't:
1. **Glean integration** (6 tools) — enterprise search across ALL company knowledge
2. **Agent Memory** (16 tools) — persistent memory with entity resolution, reasoning traces
3. **Knowledge Graph** (8 tools) — Neo4j + LightRAG, semantic search, business context
4. **Write operations** — approve PRs, transition Jira issues, add comments
5. **CLI management** (`dva mcp`) — health checks, IDE config sync, Docker lifecycle
6. **Code onboarding** — auto-detect tech stack, install matching skills
7. **Skills registry** — 62 portable agent skills (agentskills.io standard)
8. **Agent scaffolding** — `dva project create --use-case pr-reviewer`
9. **Data source management** — `dva data` for registering document/Confluence/Git sources
10. **Independent scaling** — services can be deployed/scaled independently

---

## 9. Strengths & Trade-offs Summary

| Dimension | Anchor Wins | DVA Wins |
|-----------|-------------|----------|
| **Setup simplicity** | ✅ One container, one port | |
| **Operational simplicity** | ✅ One process to monitor | |
| **Token efficiency** | ✅ Prompt workflows batch API calls | |
| **Design integration** | ✅ Figma tools | |
| **Fault isolation** | | ✅ Service-level independence |
| **Tool depth** | | ✅ More tools per integration |
| **Write operations** | | ✅ Full PR lifecycle, issue management |
| **Knowledge management** | | ✅ KG + Memory + Glean |
| **Portability** | | ✅ Skills work across any AI tool |
| **Extensibility** | | ✅ Add a new service without touching others |
| **Dev tooling** | | ✅ CLI, health checks, IDE sync |
| **Testing** | Not documented | ✅ Unit tests per service |

---

## 10. Potential Collaboration Opportunities

1. **Figma MCP** — Build a `dva-mcp-servers/figma/` service following our pattern, borrowing Anchor's tool design
2. **Prompt workflows** — Implement as Agent Skills (`.skills/jira-story-analysis/SKILL.md`) rather than server-side prompts — more portable
3. **Code search** — Add `search_code` and `list_branches` to our Bitbucket MCP
4. **Link following** — Add `get_remote_links` to our Jira MCP for Confluence/Figma traversal
5. **Shared auth** — Both teams could collaborate on the OAuth move (Anchor's roadmap)
