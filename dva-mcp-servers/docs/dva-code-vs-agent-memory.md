# DVA Code Commands vs. Neo4j Agent Memory

A comparison of our two AI-assist systems and how they complement each other.

---

## What Each System Does

### DVA Code Commands (`dva code` + `dva skill`)

**Purpose**: Project onboarding and static skill provisioning for AI code assistants.

The `dva-agentic-cli` provides a **one-time setup** workflow:

```
dva code onboard --path ./my-repo
  ↓
  1. Analyze project (languages, frameworks, deps, build tools, CI/CD, Docker, APIs)
  2. Match skills from dva-skills registry (26 skills, auto-detect via files/deps)
  3. Install .skills/<name>/SKILL.md files into the repo
  4. Generate project-context skill (auto-generated tech stack summary)
  5. Save onboard manifest (onboard.json)
  6. Register project in central tracking
```

**Commands:**

| Command | What It Does |
|---------|-------------|
| `dva code init <workspace>` | Set default workspace folder for cloning repos |
| `dva code onboard --path/--repo` | Clone + analyze + auto-install matching skills |
| `dva code list` | List all onboarded projects with tech stack summary |
| `dva code skills list` | Show skills installed in a project |
| `dva code skills available` | Show all 26 skills in the registry |
| `dva code skills add <name>` | Install a skill from registry |
| `dva code skills remove <name>` | Remove a skill |
| `dva code skills update` | Update all installed skills from latest registry |
| `dva code validate` | Validate onboarding, show readiness report |
| `dva code config --registry` | Set skills registry path/URL |
| `dva skill create <name>` | Create a new Agent Skill (agentskills.io format) |
| `dva skill install <source>` | Install skill from GitHub |
| `dva skill list` | List installed Agent Skills |
| `dva skill show <name>` | Show skill details and file tree |

**Skills Registry** (`dva-skills/registry.json` — 26 skills):

| Category | Skills |
|----------|--------|
| **Java** | java-spring-boot, java-gradle, java-maven, mapstruct, jooq, resilience4j, openapi-springdoc, spring-cloud-config, spring-cloud-contract |
| **Python** | python-fastapi, python-django, python-flask |
| **TypeScript** | typescript-react, typescript-nextjs, typescript-node |
| **Go** | go-standard |
| **Testing** | testing-junit, testing-pytest, testing-jest |
| **Database** | database-spanner, database-postgres, database-mongodb, database-bigquery, liquibase-spanner |
| **Infrastructure** | docker, ci-jenkins, ci-github-actions, gcp |
| **Messaging** | kafka-streams, apache-beam-dataflow |
| **API** | api-rest, api-grpc |
| **MCP-Powered** | jira, bitbucket, pr-reviewer |
| **Security** | security |

---

### Neo4j Agent Memory (`neo4j-agent-memory`)

**Purpose**: Dynamic, persistent, graph-stored memory that grows with every conversation.

The memory system runs **continuously** across all sessions:

```
AI Assistant (Windsurf/Cascade/Claude)
  ↓ MCP SSE (:8130)
  memory-mcp (16 tools)
  ↓ bolt://
  Neo4j (knowledge graph + vector indexes)
```

**3 Memory Types:**

| Type | What It Stores | How It Grows |
|------|---------------|-------------|
| **Short-Term** | Conversations, messages per session | Every message automatically stored |
| **Long-Term** | Entities, relationships, preferences, facts | Extracted from conversations or added explicitly |
| **Reasoning** | Decision traces, tool usage, step-by-step reasoning | Recorded when agent solves tasks |

---

## Side-by-Side Comparison

| Aspect | DVA Code Commands | Neo4j Agent Memory |
|--------|------------------|-------------------|
| **When it runs** | One-time setup (`dva code onboard`) | Continuous (every conversation) |
| **What it produces** | Static `.skills/SKILL.md` files | Dynamic graph nodes and relationships |
| **Storage** | Files in repo (git-tracked) | Neo4j graph database (persistent, queryable) |
| **Scope** | Per-project | Cross-project, cross-session |
| **Knowledge source** | Curated registry (26 human-written skills) | Agent experience (auto-extracted from conversations) |
| **Update model** | Manual (`dva code skills update`) | Automatic (learns as you work) |
| **Search** | None (files read by AI at prompt time) | Semantic vector + graph hybrid search |
| **Personalization** | None (same skills for everyone) | Per-user preferences, learned patterns |
| **Decision learning** | None | Reasoning traces record how tasks were solved |
| **Entity awareness** | Project-context skill (tech stack only) | Full knowledge graph (people, tools, services, events) |
| **Relationship tracking** | None | Typed relationships with traversal (e.g., Venkat → CREATED → Platform) |
| **Tool analytics** | None | Tool usage stats (success rates, latency per tool) |
| **Cross-IDE** | Skill files work in Claude Code, OpenCode, VS Code | MCP SSE works in any MCP client |
| **MCP integration** | Skills reference MCP servers | IS an MCP server (16 tools) |
| **Team sharing** | Via git (skills committed to repo) | Via shared Neo4j (all agents share the graph) |

---

## How They Complement Each Other

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Code Assistant                         │
│                (Windsurf / Claude / Cursor)                  │
└─────────────┬───────────────────────────┬───────────────────┘
              │                           │
     Layer 1: STATIC                Layer 2: DYNAMIC
     (DVA Code Commands)            (Neo4j Agent Memory)
              │                           │
              ▼                           ▼
┌─────────────────────────┐  ┌────────────────────────────────┐
│  .skills/SKILL.md files │  │  memory-mcp (16 MCP tools)     │
│                         │  │                                │
│  ✓ project-context      │  │  Short-Term:                   │
│    (tech stack summary) │  │    Conversation history        │
│  ✓ java-spring-boot     │  │    Context window management   │
│    (framework patterns) │  │                                │
│  ✓ database-spanner     │  │  Long-Term:                    │
│    (DB best practices)  │  │    Entities (people, tools)    │
│  ✓ testing-junit        │  │    Preferences (user patterns) │
│    (test patterns)      │  │    Facts (project knowledge)   │
│  ✓ docker               │  │    Relationships (graph)       │
│    (container patterns) │  │                                │
│  ✓ pr-reviewer          │  │  Reasoning:                    │
│    (code review flow)   │  │    Decision traces             │
│                         │  │    Tool usage analytics        │
│  Read at prompt time    │  │    "How did I solve this last   │
│  Same every session     │  │     time?" retrieval           │
└─────────────────────────┘  └────────────────────────────────┘
```

### Layer 1 answers: "What conventions should I follow?"
- Spring Boot annotation patterns
- Spanner query best practices
- JUnit test structures
- Docker multi-stage build patterns
- PR review workflow steps

### Layer 2 answers: "What do I know about THIS project and THIS user?"
- "Venkat prefers implementation-first over governance-first"
- "DVA Agentic Platform has 5 MCP servers on ports 8126-8130"
- "Last time I reviewed a Spanner PR, I flagged a missing composite index"
- "AISE Team uses Google ADK framework"
- "The Bitbucket MCP tool succeeds 98% of the time, avg 340ms"

---

## Integration Opportunities

### 1. Memory-Aware Onboarding

`dva code onboard` could store project metadata in the knowledge graph:

```python
# After analyzing a project, store entities in agent memory
await memory.long_term.add_entity(
    "cwow-patient-query-spanner", "OBJECT", subtype="REPOSITORY",
    description="Patient query service using Cloud Spanner",
    attributes={"languages": ["Java"], "framework": "Spring Boot", "database": "Spanner"},
)

await memory.long_term.add_fact(
    subject="cwow-patient-query-spanner",
    predicate="has_skills",
    obj="java-spring-boot, database-spanner, testing-junit, docker",
)
```

**Benefit**: Agent remembers project context across conversations without re-reading SKILL.md files.

### 2. Skill Usage Tracking via Reasoning Traces

When an agent uses a skill (e.g., pr-reviewer), record the trace:

```python
trace = await memory.reasoning.start_trace(
    session_id=session_id,
    task="Review PR #1936 using pr-reviewer skill",
)

# Record which tools from which skill were used
await memory.reasoning.record_tool_call(
    step_id=step.id,
    tool_name="get_pr_diff",         # from bitbucket MCP
    arguments={"pr_url": "..."},
    result="...",
    duration_ms=520,
)
```

**Benefit**: Track which skills are actually used, which tools succeed/fail, and optimize the registry.

### 3. Dynamic Skill Suggestions from Memory

Instead of static `auto_detect` rules, query the knowledge graph:

```python
# "What skills have been useful for projects like this one?"
facts = await memory.long_term.get_facts_about("cwow-patient-query-spanner")
similar_traces = await memory.reasoning.get_similar_traces(
    task="Set up AI code assist for a Spring Boot Spanner project"
)
```

**Benefit**: Skill recommendations based on actual usage patterns, not just file/dependency detection.

### 4. Preference-Driven Code Generation

Skills provide patterns, but memory provides preferences:

```
Skill says: "Use @RestController for Spring Boot REST endpoints"
Memory says: "Venkat's team prefers WebFlux reactive endpoints over servlet"
→ Agent combines both: uses reactive patterns following Spring Boot conventions
```

### 5. Cross-Project Knowledge Transfer

When onboarding a new project similar to an existing one:

```python
# Query: "What did we learn from onboarding cwow-patient-query-spanner?"
related = await memory.long_term.get_related_entities(
    entity=cwow_entity,
    relationship_types=["SIMILAR_TO", "DEPENDS_ON"],
    depth=2,
)
```

**Benefit**: Apply lessons learned from one project to another.

---

## Summary

| | DVA Code Commands | Neo4j Agent Memory | Combined |
|---|---|---|---|
| **Metaphor** | Textbook | Notebook + Experience | Expert with a textbook who takes notes |
| **Knowledge** | Curated best practices | Learned experience | Both |
| **Scope** | Per-project setup | Cross-everything | Full context |
| **Update cycle** | Manual registry updates | Automatic every conversation | Best of both |
| **Value over time** | Constant | Compounds | Accelerating |

**DVA Code Commands** give every developer the same starting point — curated, version-controlled, team-approved skills.

**Neo4j Agent Memory** makes every AI interaction build on the last — personal, contextual, ever-growing knowledge.

Together, they give AI assistants both **institutional knowledge** (skills) and **personal experience** (memory).
