# Agentic Platform
## Developer-First AI Tooling for the Village

**Presenter:** Your Name (your-user)
**Date:** April 2026
**Status:** Working Implementation — Ready for Enterprise Alignment

---

## 1. Executive Summary

The Agentic Platform is a **developer-first, implementation-driven** approach to AI-assisted software engineering at example. Rather than starting with governance frameworks and standards documents, this initiative delivers **working tools today** that connect AI code assistants directly to example's enterprise systems — Bitbucket, Jira, Confluence, and Glean.

### Key Differentiator

> **Standards describe what agents *should* do. This platform shows what agents *can* do — right now.**

| Metric | Value |
|--------|-------|
| MCP Servers Built | 4 (Bitbucket, Jira, Confluence, Glean) |
| Total AI Tools Exposed | 42 tools across all servers |
| Code Assist Skills | 26 reusable skills in registry |
| Infrastructure | Dockerized, single-command deploy |
| Time to Onboard a Repo | < 30 seconds via CLI |

---

## 2. The Problem

### Developer Pain Points Today

1. **Context Switching** — Engineers constantly alt-tab between IDE, Jira, Bitbucket, Confluence, and Glean to gather context for their work.

2. **AI Assistants Are Generic** — Tools like Windsurf/Cascade, Copilot, and OpenCode have no awareness of example-specific systems, patterns, or conventions.

3. **No Standardized Onboarding** — Every project has different conventions. New team members spend weeks understanding codebases with no automated guidance.

4. **Knowledge Silos** — Institutional knowledge lives in Confluence pages, Jira tickets, and tribal memory — inaccessible to AI assistants.

### The AISE Team's Approach (Governance-First)

The AI Strategy and Execution team is building:
- AI Risk Management Frameworks (NIST AI RMF, ISO 42001)
- Acceptable Use Policies and Intake Standards
- Agent development guidelines (Google ADK on GCP)
- Platform evaluations (Glean, Windsurf, Copilot rollout)

**This is essential work.** But governance without implementation creates shelf-ware.

### Our Approach (Implementation-First)

Build the tools. Prove the value. Then align with governance.

```
AISE (Top-Down)                    Agentic (Bottom-Up)
┌─────────────────┐               ┌─────────────────┐
│   Governance     │               │   Working Tools  │
│   Frameworks     │               │   (MCP Servers)  │
│        │         │               │        │         │
│   Standards      │               │   CLI + Skills   │
│   Documents      │               │   (Automation)   │
│        │         │               │        │         │
│   Platform       │     ◄───►     │   Docker Stack   │
│   Evaluations    │  CONVERGE     │   (Production)   │
│        │         │               │        │         │
│   Implementation │               │   Governance     │
│   (TBD)          │               │   Alignment      │
└─────────────────┘               └─────────────────┘
```

**Both paths converge.** The difference is that our path has running code at every stage.

---

## 3. What We Built

### 3.1 MCP Servers (`mcp-servers`)

The Model Context Protocol (MCP) is an open standard that lets AI assistants call external tools. We built 4 MCP servers that connect AI assistants to example systems:

#### Bitbucket MCP (Port 8126) — 15 Tools
| Tool | What It Does |
|------|-------------|
| `get_pr_overview` | Full PR summary: title, description, reviewers, status |
| `get_pr_diff` | Actual code changes in the PR |
| `get_pr_files` | List of modified files |
| `get_pr_commits` | Commit history with messages |
| `get_pr_comments` | All review comments and discussions |
| `get_pr_activities` | Timeline of PR events |
| `get_file_content` | Read any file from the repository |
| `review_pr` | AI-assisted code review |
| + 7 more | Approve, merge, comment, etc. |

**Impact:** An AI assistant can now review a PR, understand the full context, and provide intelligent feedback — without the developer leaving their IDE.

#### Jira MCP (Port 8128) — 11 Tools
| Tool | What It Does |
|------|-------------|
| `get_issue` | Full Jira ticket details |
| `search_issues` | JQL-powered search across projects |
| `get_my_issues` | Current user's assigned work |
| `get_sprint_issues` | Sprint board view |
| `add_comment` | Post updates from the IDE |
| `transition_issue` | Move tickets through workflow |
| + 5 more | Projects, assignments, config |

**Impact:** AI assistant reads the Jira ticket, understands requirements, and helps write code that matches the acceptance criteria — all in one flow.

#### Confluence MCP (Port 8129) — 10 Tools
| Tool | What It Does |
|------|-------------|
| `search_confluence` | Full-text search across wiki |
| `search_confluence_cql` | Advanced CQL queries |
| `get_confluence_page` | Read any page by ID or title |
| `list_confluence_spaces` | Browse available spaces |
| `get_child_pages` | Navigate page hierarchies |
| `get_page_comments` | Read discussions |
| `add_confluence_comment` | Post from IDE |
| + 3 more | Space details, labels, etc. |

**Impact:** AI assistant pulls architecture docs, runbooks, and design decisions from Confluence to inform code suggestions. No more "let me check the wiki."

#### Glean MCP (Port 8127) — 6 Tools
| Tool | What It Does |
|------|-------------|
| `search_glean` | Enterprise-wide knowledge search |
| `list_glean_agents` | Available Glean AI assistants |
| `chat_with_glean_agent` | Interact with Glean agents |
| `get_glean_conversation` | Retrieve chat history |
| + 2 more | Documents, datasources |

**Impact:** Unified enterprise search across all example data sources — Confluence, SharePoint, Slack, and more — accessible directly from the AI assistant.

#### Infrastructure Services
| Service | Port | Purpose |
|---------|------|---------|
| MCP Gateway | 9090 | Single endpoint aggregating all 42 tools |
| MCP Proxy | 9091 | Named server routing for tool isolation |

### 3.2 Developer Skills Registry (`skills`)

A library of **26 reusable skills** that teach AI assistants example-specific coding patterns:

| Category | Skills |
|----------|--------|
| **Java** | Spring Boot, Gradle, Maven |
| **Python** | FastAPI, Django, Flask |
| **TypeScript** | React, Next.js, Node |
| **Go** | Standard patterns |
| **Testing** | JUnit, Pytest, Jest |
| **Databases** | Spanner, PostgreSQL, MongoDB |
| **CI/CD** | Jenkins, GitHub Actions |
| **Cloud** | GCP |
| **API** | REST, gRPC |
| **Security** | Secure coding patterns |
| **Tools** | Jira (MCP), Bitbucket (MCP), PR Reviewer (MCP), Docker |

Each skill is a structured Markdown file with:
- Language/framework-specific patterns and conventions
- example coding standards
- Anti-patterns to avoid
- Auto-detection rules (file presence, dependency matching)

### 3.3 Agentic CLI (`agentic-cli`)

A command-line tool that **automates code onboarding**:

```bash
# Analyze any repo and install matching skills
`agent code onboard --path /path/to/project

# What happens:
# 1. Detects: languages, frameworks, build tools, CI/CD, databases
# 2. Matches: auto-detect rules → skills from registry
# 3. Installs: copies matched skills into .skills/ directory
# 4. Generates: project-specific context file
# 5. Configures: MCP server connections

# Result: AI assistant instantly understands the project
```

**Tested:** Successfully onboarded `agentic-cli` itself — detected Python, pyproject.toml, Make, MCP servers → installed 6 skills in < 30 seconds.

### 3.4 Knowledge Graph Infrastructure (`kg-infrastructure`)

Local development infrastructure for code knowledge graphs:

| Component | Purpose |
|-----------|---------|
| Neo4j | Graph database for code relationships |
| LightRAG | RAG pipeline for code context retrieval |
| KG MCP Server | Exposes graph queries to AI assistants |

---

## 4. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Developer's IDE                           │
│              (Windsurf / Cascade / OpenCode)                 │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Code     │  │ PR       │  │ Ticket   │  │ Wiki     │   │
│  │ Assist   │  │ Review   │  │ Context  │  │ Lookup   │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼──────────────┼──────────────┼──────────────┼────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                    MCP Gateway (:9090)                       │
│              Single SSE Endpoint for All Tools               │
├─────────────┬──────────────┬──────────────┬─────────────────┤
│ Bitbucket   │ Jira         │ Confluence   │ Glean           │
│ MCP :8126   │ MCP :8128    │ MCP :8129    │ MCP :8127       │
│ 15 tools    │ 11 tools     │ 10 tools     │ 6 tools         │
├─────────────┼──────────────┼──────────────┼─────────────────┤
│ REST API    │ REST API     │ REST API     │ REST API        │
│ v1.0        │ v2           │ Server       │ v1              │
└──────┬──────┴──────┬───────┴──────┬───────┴────────┬────────┘
       ▼             ▼              ▼                ▼
   Bitbucket       Jira        Confluence          Glean
   Server          Server      Server              Cloud
   (on-prem)       (on-prem)   (on-prem)           (SaaS)
```

### Operational Management

```bash
./mcp.sh start      # Build & start all 4 MCP services
./mcp.sh status     # Service health dashboard
./mcp.sh validate   # SSE endpoint health checks
./mcp.sh logs       # Tail service logs
./mcp.sh stop       # Graceful shutdown
```

All services are **Dockerized**, use **SSE transport** for network access, and are managed via a single `docker-compose.yml`.

---

## 5. Comparison with AISE Efforts

### Side-by-Side

| Dimension | AISE Team | Agentic Platform |
|-----------|-----------|---------------------|
| **Focus** | Governance, risk, compliance | Developer productivity, tooling |
| **Approach** | Top-down (policies → standards → implementation) | Bottom-up (tools → adoption → governance alignment) |
| **Agent Framework** | Google ADK (Python/Java) on GCP | Framework-agnostic MCP servers (any AI client) |
| **Stage** | Planning & documentation (Q2 2026 target for framework) | Working implementation (4 servers in production) |
| **Scope** | Enterprise-wide AI programs | Software engineering workflows |
| **MCP** | Listed as tool type in standards doc (Section 03) | 4 servers built, 42 tools, Docker orchestrated |
| **Agent Gateway** | Page exists (empty, TBD) | Running on port 9090, aggregates all upstreams |
| **Skills/Onboarding** | Not addressed | 26 skills, CLI automation, < 30s onboarding |
| **Knowledge Graph** | "GraphRAG Ingestion" listed in Launchpad | Neo4j + LightRAG local dev infrastructure |
| **Code Assistants** | Platform tracking (Windsurf rollout) | Actual implementation layer for Windsurf/Cascade |

### What AISE Has That We Don't
- AI Risk Management Framework (NIST, ISO 42001)
- Published AI Acceptable Use Policy
- AI Intake & Evaluation Standard
- LLM Service API (centralized Gemini/Claude gateway on Cloud Run)
- Arize observability platform integration
- Enterprise-wide AI use case registry

### What We Have That AISE Doesn't
- Working MCP server implementations
- Developer skills registry (26 skills)
- Automated code onboarding CLI
- Docker-orchestrated service stack
- Knowledge graph infrastructure
- Glean MCP integration (built, not just tracked)

---

## 6. Alignment Opportunities

### Immediate (This Quarter)

| # | Opportunity | Action | Who to Engage |
|---|------------|--------|---------------|
| 1 | **MCP Reference Implementations** | Our 4 MCP servers become the reference for AISE Section 03 "MCP Tools" standard | Manesh Gurav |
| 2 | **Agent Gateway Convergence** | Align our mcp-gateway with AISE's "Agent Gateway" platform definition | Redacted Name |
| 3 | **Windsurf-ADE Integration** | Our skills + MCP servers are the implementation for AISE's "WindSurf-ADE" platform page | Redacted Name |

### Near-Term (Next Quarter)

| # | Opportunity | Action | Who to Engage |
|---|------------|--------|---------------|
| 4 | **LLM Service API MCP** | Build an MCP server wrapping AISE's LLM Service API — gives agents access to approved Gemini/Claude models | Srujana Kandula |
| 5 | **KG → Launchpad** | Position kg-infrastructure as the dev prototype for AISE's "GraphRAG Ingestion" Launchpad service | Sanjay Arora |
| 6 | **Skills → Agent Standards** | Map our 26 skills to AISE's agent development standards (Section 03) as code-assist capabilities | Manesh Gurav |

### Strategic

| # | Opportunity | Value |
|---|------------|-------|
| 7 | **Distribution Channel** | AISE Section 09 asks "How to share agents with end users?" — our CLI + skills registry is a distribution mechanism for developer-facing agents |
| 8 | **Observability Hook** | Connect MCP server telemetry to AISE's Arize platform for enterprise-wide AI tool usage tracking |
| 9 | **Governance Compliance** | Wrap our MCP tools with AISE's AI Intake & Evaluation Standard — every tool registered as an approved AI use case |

---

## 7. Live Demo Script

### Demo 1: PR Review with AI Context (2 min)
```
1. Open a PR in Windsurf
2. AI assistant calls get_pr_overview → understands the change
3. AI calls get_pr_diff → sees the code
4. AI calls search_issues (Jira) → links to the ticket requirements
5. AI calls search_confluence → pulls relevant architecture docs
6. AI provides contextual code review with example-specific feedback
```

### Demo 2: Instant Repo Onboarding (1 min)
```
1. Clone any example repo
2. Run: agent code onboard --path ./repo
3. Show: .skills/ directory populated with matched skills
4. Open in Windsurf → AI assistant now understands the project conventions
```

### Demo 3: Management Script (30 sec)
```
1. ./mcp.sh status    → Show all services running
2. ./mcp.sh validate  → All 4 healthy with SSE streaming
3. ./mcp.sh logs confluence-mcp → Live logs
```

---

## 8. Roadmap

| Phase | Timeline | Deliverables |
|-------|----------|-------------|
| **Phase 1** (Done) | Q1 2026 | Bitbucket + Jira MCP servers, skills registry, CLI |
| **Phase 2** (Done) | Q2 2026 | Confluence + Glean MCP, Docker orchestration, management script |
| **Phase 3** (Next) | Q2-Q3 2026 | LLM Service API MCP, AISE standards alignment, KG → Launchpad |
| **Phase 4** | Q3 2026 | Enterprise rollout, Arize observability, agent distribution |

---

## 9. Ask

1. **Alignment meeting** with Manesh Gurav and Redacted Name to position MCP servers as reference implementations for AISE agent standards.

2. **Access to LLM Service API** (use case ID registration) to build the next MCP server connecting agents to approved LLM models.

3. **Pilot team** — 3-5 developers to test the full stack (CLI onboarding + MCP tools + skills) and provide feedback before broader rollout.

---

## Appendix A: Repository Links

| Repository | Bitbucket URL |
|------------|--------------|
| agentic-cli | https://bitbucket.example.com/users/your-user/repos/agentic-cli |
| dva-agent-skills | https://bitbucket.example.com/users/your-user/repos/dva-agent-skills |
| dva-agent-mcp-servers | https://bitbucket.example.com/users/your-user/repos/dva-agent-mcp-servers |
| dva-agent-kg-infra | https://bitbucket.example.com/users/your-user/repos/dva-agent-kg-infra |

## Appendix B: Port Map

| Service | Port | SSE Endpoint |
|---------|------|-------------|
| Bitbucket MCP | 8126 | http://localhost:8126/sse |
| Glean MCP | 8127 | http://localhost:8127/sse |
| Jira MCP | 8128 | http://localhost:8128/sse |
| Confluence MCP | 8129 | http://localhost:8129/sse |
| MCP Gateway | 9090 | http://localhost:9090/sse |
| MCP Proxy | 9091 | http://localhost:9091/sse |

## Appendix C: AISE Confluence Reference

| Page | ID | Key Contacts |
|------|----|-------------|
| AI Strategy and Execution (Space Home) | 1012632820 | Nason Nur |
| AI Agents - Enterprise Standards | 1117555177 | Manesh Gurav |
| AI Governance | 1032130149 | Becky Rodriguez-Crespo |
| Foundational AI Services Launchpad | (under VAIC) | Redacted Name, Sanjay Arora |
| LLM Service API Access Guide | 1170484804 | Srujana Kandula |
| example AI Target Architecture | 1170482146 | Redacted Name |
| Platforms (Agent Gateway, Windsurf-ADE) | 1016889823 | Redacted Name |
