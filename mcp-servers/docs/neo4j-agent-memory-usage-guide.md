# Neo4j Agent Memory — Usage Guide

A practical guide to using all 3 memory types in the `neo4j-agent-memory` library with real-world examples.

---

## Table of Contents

1. [Setup & Connection](#1-setup--connection)
2. [Short-Term Memory](#2-short-term-memory) — Conversations & context windows
3. [Long-Term Memory](#3-long-term-memory) — Knowledge graph, preferences, facts
4. [Reasoning Memory](#4-reasoning-memory) — Decision traces & tool usage
5. [Combined Context](#5-combined-context) — All 3 types together for LLM prompts
6. [MCP Server Usage](#6-mcp-server-usage) — Using via MCP tools from AI assistants
7. [Framework Integrations](#7-framework-integrations) — Google ADK, LangChain, etc.

---

## 1. Setup & Connection

### Install

```bash
# Core (no embeddings)
pip install neo4j-agent-memory

# With embedding provider (pick one)
pip install "neo4j-agent-memory[openai]"
pip install "neo4j-agent-memory[sentence-transformers]"  # local, no API key
pip install "neo4j-agent-memory[vertex-ai]"              # GCP

# With MCP server
pip install "neo4j-agent-memory[mcp]"

# Everything
pip install "neo4j-agent-memory[openai,mcp]"
```

### Connect

```python
import asyncio
from pydantic import SecretStr
from neo4j_agent_memory import (
    MemoryClient,
    MemorySettings,
    MemoryConfig,
    Neo4jConfig,
    EmbeddingConfig,
    EmbeddingProvider,
    ExtractionConfig,
    ExtractorType,
)

settings = MemorySettings(
    neo4j=Neo4jConfig(
        uri="bolt://localhost:7687",
        username="neo4j",
        password=SecretStr("password"),
    ),
    # Embeddings — required for semantic search, optional for CRUD
    embedding=EmbeddingConfig(
        provider=EmbeddingProvider.OPENAI,       # or SENTENCE_TRANSFORMERS
        model="text-embedding-3-small",
        dimensions=1536,
    ),
    # Entity extraction — auto-extract entities from messages
    extraction=ExtractionConfig(
        extractor_type=ExtractorType.NONE,       # NONE, GLINER, LLM, HYBRID
    ),
    # Memory behavior
    memory=MemoryConfig(
        message_embedding_enabled=True,          # embed messages for search
        trace_embedding_enabled=True,            # embed traces for similar-task retrieval
    ),
)

# Use as async context manager (recommended)
async with MemoryClient(settings) as memory:
    # memory.short_term, memory.long_term, memory.reasoning are ready
    stats = await memory.get_stats()
    print(stats)
```

### Minimal Setup (no embeddings, no extraction)

```python
settings = MemorySettings(
    neo4j=Neo4jConfig(
        uri="bolt://localhost:7687",
        username="neo4j",
        password=SecretStr("password"),
    ),
    embedding=EmbeddingConfig(provider=EmbeddingProvider.CUSTOM, dimensions=384),
    extraction=ExtractionConfig(extractor_type=ExtractorType.NONE),
    memory=MemoryConfig(message_embedding_enabled=False, trace_embedding_enabled=False),
)
```

---

## 2. Short-Term Memory

**Purpose**: Conversation history and session management. Think of it as the agent's working memory — what was said in this conversation.

### Key Methods

| Method | Description |
|--------|-------------|
| `add_message()` | Store a message in a session |
| `get_conversation()` | Get full conversation history |
| `list_sessions()` | Browse all sessions |
| `search_messages()` | Semantic search across messages |
| `get_context()` | Get formatted context for LLM |
| `summarize_session()` | Generate conversation summary |

### 2.1 Store Messages

```python
async with MemoryClient(settings) as memory:
    session_id = "sprint-planning-2026-04-06"

    # User message
    msg1 = await memory.short_term.add_message(
        session_id=session_id,
        role="user",
        content="What's the status of the MCP gateway? We need it ready for the AISE demo.",
        metadata={"source": "windsurf", "user": "your-user"},
    )

    # Assistant response
    msg2 = await memory.short_term.add_message(
        session_id=session_id,
        role="assistant",
        content="The MCP gateway is operational on port 9090, aggregating 5 upstream services: "
                "Bitbucket (8126), Glean (8127), Jira (8128), Confluence (8129), and Memory (8130).",
    )

    # System event
    msg3 = await memory.short_term.add_message(
        session_id=session_id,
        role="system",
        content="Deployment completed: memory-mcp service started on port 8130.",
        metadata={"event": "deployment", "service": "memory-mcp"},
    )

    print(f"Stored: {msg1.id}, {msg2.id}, {msg3.id}")
```

### 2.2 Retrieve Conversations

```python
    # Get full conversation
    conv = await memory.short_term.get_conversation(
        session_id=session_id,
        limit=50,  # max messages to return
    )
    for msg in conv.messages:
        print(f"  [{msg.role}] {msg.content[:80]}...")

    # List all sessions
    sessions = await memory.short_term.list_sessions(limit=20)
    for s in sessions:
        print(f"  {s.session_id}: {s.message_count} msgs, last: {s.last_message_preview}")
```

### 2.3 Search Messages (requires embeddings)

```python
    # Semantic search across all conversations
    results = await memory.short_term.search_messages(
        query="MCP gateway deployment status",
        session_id=None,          # None = search all sessions
        limit=5,
        threshold=0.7,            # similarity threshold (0.0-1.0)
    )
    for msg in results:
        print(f"  [{msg.role}] {msg.content[:100]}")
```

### 2.4 Get Formatted Context for LLM

```python
    # Returns a formatted string ready for system prompt injection
    context = await memory.short_term.get_context(
        query="What tools do we have?",
        session_id=session_id,
        max_messages=10,
    )
    # context = "### Recent Conversation\n**user**: What's the status..."
    print(context)
```

### Use Cases

- **Conversation continuity** — Resume conversations across sessions
- **Context window management** — Retrieve only relevant past messages
- **Multi-session awareness** — Search across all conversations for relevant history
- **Audit trail** — Track what was said and when, with metadata

---

## 3. Long-Term Memory

**Purpose**: Persistent knowledge graph with entities, relationships, preferences, and facts. This is the agent's durable knowledge — things it learns and remembers permanently.

### Key Methods

| Category | Methods |
|----------|---------|
| **Entities** | `add_entity()`, `search_entities()`, `get_entity_by_name()`, `get_related_entities()`, `get_entity_relationships()` |
| **Relationships** | `add_relationship()`, `get_entity_relationships()`, `get_related_entities()` |
| **Preferences** | `add_preference()`, `search_preferences()`, `get_preferences_by_category()` |
| **Facts** | `add_fact()`, `search_facts()`, `get_facts_about()` |
| **Dedup** | `merge_duplicate_entities()`, `review_duplicate()`, `get_same_as_cluster()`, `get_deduplication_stats()` |
| **Provenance** | `link_entity_to_message()`, `link_entity_to_extractor()`, `get_entity_provenance()` |

### 3.1 Entity Management (POLE+O Model)

The library uses the **POLE+O** entity type model:
- **P**erson — People, users, contacts
- **O**bject — Software, tools, documents, artifacts
- **L**ocation — Cities, addresses, geographic features
- **E**vent — Meetings, deployments, incidents
- **O**rganization — Companies, teams, departments

```python
async with MemoryClient(settings) as memory:
    # Create entities (returns tuple: Entity, DeduplicationResult)
    opts = dict(generate_embedding=False, deduplicate=False, geocode=False, enrich=False)

    example, _ = await memory.long_term.add_entity(
        name="example",
        entity_type="ORGANIZATION",
        description="Healthcare company, largest dialysis provider in the US",
        aliases=["DVA", "example Inc."],
        **opts,
    )

    venkat, _ = await memory.long_term.add_entity(
        name="Your Name",
        entity_type="PERSON",
        description="AI Platform Engineer, Agentic Platform developer",
        attributes={"team": "Engineering", "role": "Senior Engineer"},
        **opts,
    )

    platform, _ = await memory.long_term.add_entity(
        name="Agentic Platform",
        entity_type="OBJECT",
        subtype="SOFTWARE",
        description="Developer-first AI tooling platform with MCP servers, skills registry, and CLI",
        **opts,
    )

    demo_event, _ = await memory.long_term.add_entity(
        name="AISE Demo April 2026",
        entity_type="EVENT",
        description="Presentation of Agentic Platform to AISE governance team",
        attributes={"date": "2026-04-15", "audience": "AISE Team"},
        **opts,
    )

    aise, _ = await memory.long_term.add_entity(
        name="AISE Team",
        entity_type="ORGANIZATION",
        subtype="DEPARTMENT",
        description="AI Strategy and Execution team at example, handles governance",
        **opts,
    )
```

### 3.2 Relationships

```python
    # Create typed relationships between entities
    await memory.long_term.add_relationship(
        source=venkat,
        target=platform,
        relationship_type="CREATED",
        description="Built the Agentic Platform",
        confidence=1.0,
    )

    await memory.long_term.add_relationship(
        source=platform,
        target=example,
        relationship_type="BUILT_FOR",
        description="Platform serves example engineering teams",
    )

    await memory.long_term.add_relationship(
        source=aise,
        target=example,
        relationship_type="PART_OF",
        description="AISE is example's AI governance organization",
    )

    await memory.long_term.add_relationship(
        source=demo_event,
        target=aise,
        relationship_type="PRESENTED_TO",
        description="Demo of platform capabilities to AISE team",
    )

    # Query relationships
    relationships = await memory.long_term.get_entity_relationships("Agentic Platform")
    for entity, rel in relationships:
        print(f"  {rel.relationship_type} -> {entity.display_name}")

    # Graph traversal: get related entities up to 2 hops away
    related = await memory.long_term.get_related_entities(
        platform,
        relationship_types=None,   # all types
        depth=2,                   # traverse up to 2 hops
    )
    for entity, rel in related:
        print(f"  {entity.display_name} ({entity.type}) via {rel.relationship_type}")
```

### 3.3 Preferences

```python
    # Store user/team preferences for personalization
    p1 = await memory.long_term.add_preference(
        category="architecture",
        preference="Prefers implementation-first approach over governance-first",
        context="Venkat prioritizes working code and demos over design docs",
        confidence=0.95,
        generate_embedding=False,
    )

    p2 = await memory.long_term.add_preference(
        category="technology",
        preference="Uses FastMCP with SSE transport for Docker deployments",
        generate_embedding=False,
    )

    p3 = await memory.long_term.add_preference(
        category="communication",
        preference="Prefers terse, direct responses without acknowledgment phrases",
        generate_embedding=False,
    )

    p4 = await memory.long_term.add_preference(
        category="code_style",
        preference="Python 3.12+, pydantic-settings for config, httpx for HTTP clients",
        generate_embedding=False,
    )

    # Retrieve by category
    arch_prefs = await memory.long_term.get_preferences_by_category("architecture")
    for pref in arch_prefs:
        print(f"  [{pref.category}] {pref.preference} (confidence: {pref.confidence})")

    # Semantic search across all preferences (requires embeddings)
    # results = await memory.long_term.search_preferences("how to deploy services")
```

### 3.4 Facts (Subject-Predicate-Object Triples)

```python
    from datetime import datetime

    f1 = await memory.long_term.add_fact(
        subject="Agentic Platform",
        predicate="has_mcp_servers",
        obj="5 (Bitbucket:8126, Glean:8127, Jira:8128, Confluence:8129, Memory:8130)",
        confidence=1.0,
        generate_embedding=False,
    )

    f2 = await memory.long_term.add_fact(
        subject="Agentic Platform",
        predicate="total_tools",
        obj="58+ tools across all MCP servers",
        generate_embedding=False,
    )

    f3 = await memory.long_term.add_fact(
        subject="AISE Team",
        predicate="uses_framework",
        obj="Google ADK (Agent Development Kit)",
        generate_embedding=False,
    )

    f4 = await memory.long_term.add_fact(
        subject="DVA Skills Registry",
        predicate="skill_count",
        obj="26 reusable developer skills",
        valid_from=datetime(2026, 3, 1),  # temporal validity
        generate_embedding=False,
    )

    # Query facts about a subject
    facts = await memory.long_term.get_facts_about("Agentic Platform")
    for fact in facts:
        print(f"  {fact.subject} —{fact.predicate}→ {fact.obj}")

    # Semantic search (requires embeddings)
    # results = await memory.long_term.search_facts("how many tools")
```

### 3.5 Entity Deduplication

When embeddings are enabled, entities are automatically checked for duplicates on creation:

```python
    # With dedup enabled (default), this returns DeduplicationResult
    entity, dedup_result = await memory.long_term.add_entity(
        name="Da Vita Inc",
        entity_type="ORGANIZATION",
        description="Healthcare company",
        deduplicate=True,          # check for similar existing entities
        generate_embedding=True,   # needed for dedup
    )

    if dedup_result.is_duplicate:
        print(f"  Duplicate detected! Action: {dedup_result.action}")
        print(f"  Matched: {dedup_result.matched_entity_name}")
        print(f"  Similarity: {dedup_result.similarity_score}")
        # action = 'merged' (auto-merged) or 'flagged' (needs review)
    else:
        print(f"  New entity created: {entity.display_name}")

    # Manual dedup review
    # await memory.long_term.review_duplicate(source_id, target_id, confirm=True)
    # await memory.long_term.merge_duplicate_entities(source_id, target_id)
```

### 3.6 Provenance (Entity ↔ Message Linking)

```python
    # Link an entity to the message it was extracted from
    await memory.long_term.link_entity_to_message(
        entity=platform,
        message_id=msg1.id,         # from short-term memory
        confidence=0.9,
        context="Mentioned in sprint planning discussion",
    )

    # Query provenance
    provenance = await memory.long_term.get_entity_provenance(platform)
    print(f"  Entity: {provenance}")
    # Shows which messages, extractors, and sessions contributed to this entity
```

### Use Cases

- **Project knowledge base** — Store entities for repos, services, team members
- **User profiling** — Remember preferences across sessions
- **Fact tracking** — Declarative knowledge with temporal validity
- **Entity resolution** — Deduplicate mentions of the same entity across conversations
- **Provenance** — Track where knowledge came from (which conversation, which extractor)

---

## 4. Reasoning Memory

**Purpose**: Record and learn from decision-making processes. Think of it as the agent's experience — how it solved tasks before and what tools worked.

### Key Methods

| Category | Methods |
|----------|---------|
| **Traces** | `start_trace()`, `complete_trace()`, `get_trace()`, `get_trace_with_steps()`, `list_traces()` |
| **Steps** | `add_step()` (thought/action/observation cycle) |
| **Tool Calls** | `record_tool_call()`, `get_tool_stats()`, `get_tool_usage_stats()` |
| **Search** | `get_similar_traces()`, `get_session_traces()`, `get_context()` |

### 4.1 Record a Reasoning Trace

A trace captures the full decision-making process for a task:

```python
async with MemoryClient(settings) as memory:
    session_id = "pr-review-2026-04-06"

    # Start a new trace
    trace = await memory.reasoning.start_trace(
        session_id=session_id,
        task="Review PR #1936: IMTO-3008 patient query optimization",
        metadata={
            "pr_url": "https://bitbucket.example.com/projects/CGP/repos/cwow-patient-query-spanner/pull-requests/1936",
            "complexity": "high",
            "model": "claude-sonnet-4-20250514",
        },
    )
    print(f"Started trace: {trace.id}")
```

### 4.2 Record Steps (Thought → Action → Observation)

Each step follows the ReAct pattern:

```python
    # Step 1: Understand the PR
    step1 = await memory.reasoning.add_step(
        trace_id=trace.id,
        thought="Need to understand what this PR changes. Start with overview and diff.",
        action="Call get_pr_overview and get_pr_diff tools",
        observation="PR modifies 3 files in patient-query module. Changes Spanner query "
                    "from full table scan to indexed lookup. Adds new composite index.",
    )

    # Record the tool call that happened during this step
    await memory.reasoning.record_tool_call(
        step_id=step1.id,
        tool_name="get_pr_overview",
        arguments={"pr_url": "https://bitbucket.example.com/.../pull-requests/1936"},
        result="PR #1936: 3 files changed, +45 -12 lines",
        status="success",
        duration_ms=340,
    )

    await memory.reasoning.record_tool_call(
        step_id=step1.id,
        tool_name="get_pr_diff",
        arguments={"pr_url": "https://bitbucket.example.com/.../pull-requests/1936"},
        result="Diff shows query optimization in PatientQueryService.java...",
        status="success",
        duration_ms=520,
    )

    # Step 2: Check for issues
    step2 = await memory.reasoning.add_step(
        trace_id=trace.id,
        thought="The index change looks good but I should verify the query plan "
                "and check if the index covers all query patterns.",
        action="Analyze the Spanner query patterns and index definition",
        observation="Index covers the primary query pattern. However, the secondary "
                    "query in line 87 still uses a full scan. Recommend adding it to the index.",
    )

    # Step 3: Provide review
    step3 = await memory.reasoning.add_step(
        trace_id=trace.id,
        thought="Overall the PR improves performance. One issue to flag.",
        action="Post review comment about secondary query optimization",
        observation="Comment posted. Approved PR with suggestion.",
    )

    await memory.reasoning.record_tool_call(
        step_id=step3.id,
        tool_name="add_pr_comment",
        arguments={
            "pr_url": "https://bitbucket.example.com/.../pull-requests/1936",
            "text": "Consider adding patientId to the composite index for the secondary query.",
            "file_path": "src/main/java/PatientQueryService.java",
            "line": 87,
        },
        result="Comment added successfully",
        status="success",
        duration_ms=280,
    )
```

### 4.3 Complete the Trace

```python
    # Mark the trace as complete with outcome
    completed = await memory.reasoning.complete_trace(
        trace_id=trace.id,
        outcome="Approved PR with one suggestion: extend composite index to cover "
                "secondary query pattern. Performance improvement validated.",
        success=True,
    )
    print(f"Trace completed: {completed.id}, steps: {len(completed.steps)}")
```

### 4.4 Learn from Past Traces

```python
    # Find similar past tasks (requires embeddings)
    similar = await memory.reasoning.get_similar_traces(
        task="Review PR for database query optimization",
        limit=3,
        success_only=True,         # only successful traces
        threshold=0.7,
    )
    for t in similar:
        print(f"  Similar task: {t.task}")
        print(f"  Outcome: {t.outcome}")
        print(f"  Steps: {len(t.steps)}")

    # Get all traces for a session
    session_traces = await memory.reasoning.get_session_traces(session_id)

    # List traces with filters
    recent = await memory.reasoning.list_traces(
        success_only=True,
        limit=10,
        order_by="completed_at",
        order_dir="desc",
    )
```

### 4.5 Tool Usage Analytics

```python
    # Get stats for a specific tool
    stats = await memory.reasoning.get_tool_stats("get_pr_diff")
    for s in stats:
        print(f"  Tool: {s.name}, calls: {s.total_calls}, "
              f"success_rate: {s.success_rate:.0%}, avg_time: {s.avg_duration_ms}ms")

    # Get stats for ALL tools
    all_tools = await memory.reasoning.get_tool_usage_stats()
    for name, tool in all_tools.items():
        print(f"  {name}: {tool.total_calls} calls, {tool.success_rate:.0%} success")
```

### 4.6 Get Formatted Context for LLM

```python
    # Returns formatted text showing how similar tasks were solved
    reasoning_context = await memory.reasoning.get_context(
        query="How to review a database optimization PR",
        max_traces=3,
    )
    # reasoning_context = "### Similar Past Tasks\n**Task**: Review PR for database..."
    print(reasoning_context)
```

### Use Cases

- **Learning from experience** — Agent improves by recalling how similar tasks were solved
- **Tool selection** — Know which tools work best for which tasks
- **Debugging** — Full audit trail of agent decision-making
- **Performance tracking** — Tool call success rates and latency
- **Pattern recognition** — Identify common reasoning patterns across tasks

---

## 5. Combined Context

The `MemoryClient.get_context()` method assembles all 3 memory types into a single context string for LLM prompts:

```python
async with MemoryClient(settings) as memory:
    # Get combined context from all memory types
    context = await memory.get_context(
        query="What MCP servers do we have and how should I deploy them?",
        session_id="sprint-planning-2026-04-06",
        include_short_term=True,     # conversation history
        include_long_term=True,      # entities, preferences, facts
        include_reasoning=True,      # similar past task traces
        max_items=10,                # max items per type
    )

    # Returns formatted string like:
    # ## Conversation History
    # ### Recent Conversation
    # **user**: What's the status of the MCP gateway?
    # **assistant**: The MCP gateway is operational on port 9090...
    #
    # ## Relevant Knowledge
    # ### Entities
    # - Agentic Platform (OBJECT): Developer-first AI tooling platform...
    # ### Preferences
    # - [technology] Uses FastMCP with SSE transport for Docker deployments
    # ### Facts
    # - Agentic Platform has_mcp_servers: 5 servers...
    #
    # ## Similar Past Tasks
    # **Task**: Deploy Confluence MCP server
    # **Outcome**: Successfully created server with 10 tools on port 8129

    # Inject into LLM system prompt
    system_prompt = f"""You are a helpful AI assistant.

Here is relevant context from memory:

{context}

Use this context to provide informed responses."""
```

### Memory Stats

```python
    stats = await memory.get_stats()
    # {
    #   "conversations": 3,
    #   "messages": 24,
    #   "entities": 12,
    #   "preferences": 4,
    #   "facts": 6,
    #   "traces": 5
    # }
```

### Graph Export (for visualization)

```python
    from datetime import datetime, timedelta

    graph = await memory.get_graph(
        memory_types=["short_term", "long_term", "reasoning"],
        session_id=None,               # all sessions
        since=datetime.now() - timedelta(days=7),
        include_embeddings=False,      # smaller payload
        limit=500,
    )
    print(f"Nodes: {len(graph.nodes)}, Relationships: {len(graph.relationships)}")
    # Export for NVL, D3.js, or any graph visualization library
```

---

## 6. MCP Server Usage

The library ships with a built-in MCP server (16 tools) that can be used by any MCP-compatible client (Windsurf, Claude Desktop, Cursor, etc.)

### Start the Server

```bash
# SSE transport (Docker / network)
neo4j-agent-memory mcp serve \
  --transport sse \
  --port 8130 \
  --host 0.0.0.0 \
  --password <neo4j-password> \
  --profile extended \
  --session-strategy per_day

# stdio transport (local IDE integration)
neo4j-agent-memory mcp serve --password <neo4j-password>
```

### Windsurf Configuration

```json
{
  "mcpServers": {
    "memory": {
      "serverUrl": "http://localhost:8130/sse"
    }
  }
}
```

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "neo4j-memory": {
      "command": "neo4j-agent-memory",
      "args": ["mcp", "serve", "--password", "your-password"]
    }
  }
}
```

### Tool Mapping (MCP ↔ Python API)

| MCP Tool | Python API |
|----------|-----------|
| `memory_store_message` | `memory.short_term.add_message()` |
| `memory_get_conversation` | `memory.short_term.get_conversation()` |
| `memory_list_sessions` | `memory.short_term.list_sessions()` |
| `memory_get_context` | `memory.get_context()` |
| `memory_search` | `memory.short_term.search_messages()` + `long_term.search_entities()` |
| `memory_add_entity` | `memory.long_term.add_entity()` |
| `memory_add_preference` | `memory.long_term.add_preference()` |
| `memory_add_fact` | `memory.long_term.add_fact()` |
| `memory_get_entity` | `memory.long_term.get_entity_by_name()` |
| `memory_create_relationship` | `memory.long_term.add_relationship()` |
| `memory_export_graph` | `memory.get_graph()` |
| `memory_start_trace` | `memory.reasoning.start_trace()` |
| `memory_record_step` | `memory.reasoning.add_step()` + `record_tool_call()` |
| `memory_complete_trace` | `memory.reasoning.complete_trace()` |
| `memory_get_observations` | Observer integration (auto-summarization) |
| `graph_query` | `memory.graph.execute_read()` (read-only Cypher) |

---

## 7. Framework Integrations

### Google ADK (AISE alignment)

```python
from neo4j_agent_memory.integrations.google_adk import Neo4jMemoryService

# Requires: pip install "neo4j-agent-memory[google-adk]"
memory_service = Neo4jMemoryService(settings)

# Use with Google ADK Agent
from google.adk import Agent
agent = Agent(
    name="dva-agent",
    memory_service=memory_service,
)
```

### LangChain

```python
from neo4j_agent_memory.integrations.langchain import Neo4jChatMessageHistory

# Requires: pip install "neo4j-agent-memory[langchain]"
history = Neo4jChatMessageHistory(
    session_id="my-session",
    settings=settings,
)
```

### Pydantic AI

```python
from neo4j_agent_memory.integrations.pydantic_ai import Neo4jMessageHistory

# Requires: pip install "neo4j-agent-memory[pydantic-ai]"
```

---

## Quick Reference

### Entity Types (POLE+O)
| Type | Examples |
|------|---------|
| `PERSON` | Team members, users, contacts |
| `OBJECT` | Software, tools, documents, APIs |
| `LOCATION` | Offices, cities, regions |
| `EVENT` | Deployments, meetings, incidents |
| `ORGANIZATION` | Companies, teams, departments |

### Session Strategies
| Strategy | Behavior |
|----------|----------|
| `per_conversation` | New session ID per MCP connection |
| `per_day` | Same session ID for all conversations on the same day |
| `persistent` | Single session ID for the user (never rotates) |

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j connection URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | (required) | Neo4j password |
| `NEO4J_DATABASE` | `neo4j` | Neo4j database name |
| `OPENAI_API_KEY` | — | Required for OpenAI embeddings |
