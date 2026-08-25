# KEEL KG Infrastructure — Cleanup Audit

**Date:** 2026-04-06  
**Status:** Completed

## Summary

Audit and cleanup of memory/KG-related projects in the workspace to eliminate redundancy, fix infrastructure issues, and prepare for domain-specific knowledge indexing via MCP.

---

## Issues Found & Fixed

### 1. Abandoned `lightrag-infrastructure/` Directory
- **Issue:** Empty directory at project root with only empty `config/`, `lib/`, `scripts/` subdirectories
- **Root cause:** LightRAG setup moved to `kg-infrastructure/lightrag/` but old dir was left behind
- **Fix:** Deleted `lightrag-infrastructure/`
- **Impact:** LightRAG container was crash-looping because its volume mounts pointed to the deleted directory

### 2. LightRAG Container Crash-Loop
- **Issue:** `keel-lightrag` container failing with `can't open file '/app/scripts/server.py'`
- **Root cause:** Container was started from old `lightrag-infrastructure/` compose file, volume mounts pointed to empty dirs
- **Fix:** Stopped old container, restarted from `kg-infrastructure/lightrag/docker-compose.yml`
- **Status:** Container now healthy on port 8001

### 3. Isolated Docker Networks (3 separate `keel-network` bridges)
- **Issue:** Three separate Docker networks instead of one shared network:
  - `keel-network` (shared, used by kg-mcp and mcp-servers)
  - `lightrag-infrastructure_keel-network` (orphaned)
  - `neo4j-infrastructure_keel-network` (isolated — Neo4j was unreachable from other services)
- **Root cause:** Each docker-compose.yml defined `keel-network` as `driver: bridge` instead of `external: true`
- **Fix:**
  - Changed `kg-infrastructure/lightrag/docker-compose.yml` network to `external: true`
  - Changed `kg-infrastructure/neo4j/docker-compose.yml` network to `external: true`
  - Connected `keel-neo4j` container to shared `keel-network`
  - Removed orphaned networks
- **Status:** Single `keel-network` now shared by all services

### 4. Neo4j Namespace Collision (Entity label)
- **Issue:** Both `neo4j-agent-memory` (memory-mcp) and `keel kg ingest` create nodes with `Entity` label in the same Neo4j instance
- **Memory-mcp labels:** `Conversation`, `Message`, `Entity`, `Preference`, `Fact`, `ReasoningTrace`, `ReasoningStep`, `Tool`, `ToolCall`
- **KG ingest labels:** Dynamic from LLM (`Patient`, `Facility`, etc.), `Code::*` for git repos, `Document`, falls back to `Entity`
- **Fixes applied:**
  - `entity_extraction.py`: Default entity type changed from `Entity` → `KGEntity`
  - `neo4j_client.py`: `sanitize_label()` fallback changed from `Entity` → `KGEntity`
  - `ingest.py`: Added `_source: "keel_kg"` property to all ingested nodes
  - `neo4j_client.py`: `get_stats()` queries scoped to `WHERE n._source = 'agent_kg'`
  - `neo4j_client.py`: Vector index renamed from `entity_embeddings` → `kg_entity_embeddings` on `KGEntity` label
  - `search.py`: Exact search scoped to `WHERE n._source = 'agent_kg'`
  - `query.py`: All simple Cypher patterns scoped to `WHERE n._source = 'agent_kg'`
  - `query.py`: Vertex AI prompt updated to always include `_source` filter
  - **CRITICAL:** `kg.py` clear command changed from `MATCH (n) DETACH DELETE n` to `MATCH (n) WHERE n._source = 'agent_kg' DETACH DELETE n` — prevents accidental deletion of memory-mcp data

### 5. kg-mcp Not Standard MCP (Assessment Only)
- **Issue:** `kg-infrastructure/kg-mcp/` uses custom FastAPI HTTP endpoints, NOT MCP SSE/stdio transport
- **Impact:** Cannot be used by Windsurf, Claude Desktop, or the mcp-gateway
- **Current state:** Running on port 8125, functional but isolated
- **Recommendation:** Rebuild as proper FastMCP SSE server in `mcp-servers/kg/` (Phase 1 task)
- **No code change made** — this is a build task, not a cleanup task

---

## Files Modified

| File | Change |
|------|--------|
| `kg-infrastructure/lightrag/docker-compose.yml` | Network → `external: true` |
| `kg-infrastructure/neo4j/docker-compose.yml` | Network → `external: true` |
| `agentic-cli/.../kg/entity_extraction.py` | Default type `Entity` → `KGEntity` |
| `agentic-cli/.../kg/neo4j_client.py` | `sanitize_label` fallback, scoped `get_stats`, renamed vector index |
| `agentic-cli/.../kg/ingest.py` | Added `_source: "keel_kg"` to all nodes |
| `agentic-cli/.../kg/search.py` | Scoped exact search to `_source = 'agent_kg'` |
| `agentic-cli/.../kg/query.py` | Scoped all Cypher patterns + Vertex AI prompt |
| `agentic-cli/.../commands/kg.py` | Scoped `clear` command to `_source = 'agent_kg'` |

## Files/Dirs Deleted

| Path | Reason |
|------|--------|
| `lightrag-infrastructure/` | Abandoned empty directory, real LightRAG at `kg-infrastructure/lightrag/` |

## Docker Changes

| Action | Detail |
|--------|--------|
| Removed `lightrag-infrastructure_keel-network` | Orphaned network |
| Removed `neo4j-infrastructure_keel-network` | Isolated network, Neo4j moved to shared |
| Reconnected `keel-neo4j` to `keel-network` | Was on isolated network |
| Restarted `keel-lightrag` from correct compose | Now mounts correct `scripts/server.py` |

---

## Current Docker State (Post-Cleanup)

```
CONTAINER          PORT    STATUS    NETWORK
keel-neo4j          7687    healthy   keel-network
keel-lightrag       8001    healthy   keel-network
keel-kg-mcp         8125    healthy   keel-network
```

## Neo4j Label Namespace (Post-Cleanup)

| Label | Owner | Purpose |
|-------|-------|---------|
| `Conversation` | memory-mcp | Short-term memory sessions |
| `Message` | memory-mcp | Short-term memory messages |
| `Entity` | memory-mcp | Long-term memory entities (POLE+O) |
| `Person` | memory-mcp | Entity subtype |
| `Organization` | memory-mcp | Entity subtype |
| `Object` | memory-mcp | Entity subtype |
| `Preference` | memory-mcp | Long-term memory preferences |
| `Fact` | memory-mcp | Long-term memory facts |
| `ReasoningTrace` | memory-mcp | Reasoning memory |
| `ReasoningStep` | memory-mcp | Reasoning memory |
| `Tool` | memory-mcp | Tool catalog |
| `ToolCall` | memory-mcp | Reasoning memory |
| `KGEntity` | agent kg | Default fallback for extracted entities |
| `Patient` | agent kg | Domain entity (from LLM extraction) |
| `Facility` | agent kg | Domain entity (from LLM extraction) |
| `Code::*` | agent kg | Code entities (git repos) |
| `Document` | agent kg | Raw documents (no extraction) |

**Disambiguation:** All agent kg nodes have `_source: "keel_kg"` property.

---

## Next Steps (Not Part of Cleanup)

1. **Phase 1:** Build proper kg-mcp with FastMCP SSE in `mcp-servers/kg/`, wire into gateway
2. **Phase 2:** Index business requirements using `keel kg ingest` + LightRAG workspaces
3. **Phase 3:** Link `keel code onboard` to KG workspaces for per-project context
4. **Phase 4:** Configure coding tools to use gateway for business requirements context via MCP
