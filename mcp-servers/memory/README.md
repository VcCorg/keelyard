# Memory MCP — Neo4j Agent Memory

Graph-native memory system for AI agents, powered by [neo4j-agent-memory](https://github.com/neo4j-labs/agent-memory).

## Overview

This service wraps the open-source `neo4j-agent-memory` package as an MCP server, providing AI assistants with persistent memory across 3 tiers:

| Memory Type | What It Stores | Use Case |
|------------|---------------|----------|
| **Short-Term** | Conversations & messages per session | Conversation history, context window management |
| **Long-Term** | Entities, preferences, facts (knowledge graph) | User preferences, project knowledge, entity resolution |
| **Reasoning** | Decision traces, tool usage patterns | Learn from past decisions, similar task retrieval |

## Tools (16 — Extended Profile)

### Core (6 tools)
| Tool | Type | Description |
|------|------|-------------|
| `memory_search` | Read | Hybrid vector + graph search across all memory types |
| `memory_get_context` | Read | Assembled context from all memory types for LLM prompts |
| `memory_store_message` | Write | Store messages with auto entity/preference extraction |
| `memory_add_entity` | Write | Create/update entities with POLE+O types and dedup |
| `memory_add_preference` | Write | Record user preferences for personalization |
| `memory_add_fact` | Write | Store subject-predicate-object fact triples |

### Extended (10 additional tools)
| Tool | Type | Description |
|------|------|-------------|
| `memory_get_conversation` | Read | Full conversation history for a session |
| `memory_list_sessions` | Read | Browse stored conversation sessions |
| `memory_get_entity` | Read | Entity details with graph neighbor traversal |
| `memory_export_graph` | Read | Export subgraph as JSON for visualization |
| `memory_create_relationship` | Write | Create typed relationships between entities |
| `memory_start_trace` | Write | Begin recording a reasoning trace |
| `memory_record_step` | Write | Record a thought-action-observation step |
| `memory_complete_trace` | Write | Complete a reasoning trace with outcome |
| `memory_get_observations` | Read | Get observations and extracted insights |
| `graph_query` | Read | Execute read-only Cypher queries |

## Quick Start

### Docker (with existing Neo4j)

```bash
# Requires Neo4j running on dva-network (from dva-kg-infrastructure)
docker compose up -d memory-mcp
```

### Standalone (local dev)

```bash
pip install "neo4j-agent-memory[mcp]"

# SSE transport (network)
neo4j-agent-memory mcp serve --transport sse --port 8130 --password <neo4j-pw>

# stdio transport (IDE integration)
neo4j-agent-memory mcp serve --password <neo4j-pw>
```

### Windsurf / Cascade Configuration

```json
{
  "mcpServers": {
    "memory": {
      "serverUrl": "http://localhost:8130/sse"
    }
  }
}
```

## Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `NEO4J_URI` | `bolt://dva-neo4j:7687` | Neo4j connection URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | (required) | Neo4j password |
| `NEO4J_DATABASE` | `neo4j` | Neo4j database name |

## Requirements

- Neo4j 5.20+ (for vector indexes)
- Python 3.10+
- Network access to Neo4j instance

## Architecture

```
AI Assistant (Windsurf/Cascade)
        │
        ▼ SSE (:8130)
┌─────────────────────┐
│   memory-mcp        │  neo4j-agent-memory CLI
│   16 MCP tools      │  FastMCP server
│                     │
│  ┌───────────────┐  │
│  │ Short-Term    │  │  Conversations, messages
│  │ Long-Term     │  │  Entities (POLE+O), preferences, facts
│  │ Reasoning     │  │  Decision traces, tool usage
│  └───────┬───────┘  │
└──────────┼──────────┘
           │ bolt://
           ▼
    ┌──────────────┐
    │   Neo4j      │  Graph database
    │   :7687      │  Vector indexes for hybrid search
    └──────────────┘
```

## Tested Capabilities

All 3 memory types verified against Neo4j 5.14 (community):

- **Short-term**: Store/retrieve messages, conversation history, session management
- **Long-term**: Add entities (ORGANIZATION, PERSON, OBJECT) with relationships, preferences, facts
- **Reasoning**: Start/step/complete traces with tool call recording
- **Combined context**: `get_context()` assembles all 3 types into LLM-ready format
- **MCP SSE**: All 16 tools accessible via FastMCP SSE endpoint
- **Cypher queries**: Read-only graph queries via `graph_query` tool

## Embedding Support

For vector search and semantic matching, install an embedding provider:

```bash
pip install "neo4j-agent-memory[openai]"          # OpenAI embeddings
pip install "neo4j-agent-memory[sentence-transformers]"  # Local models
pip install "neo4j-agent-memory[vertex-ai]"        # GCP Vertex AI
```

Without embeddings, the service still works for all CRUD operations — only `memory_search` and `memory_get_context` lose semantic similarity features.
