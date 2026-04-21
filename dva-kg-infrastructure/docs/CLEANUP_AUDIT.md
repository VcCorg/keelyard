# DVA KG Infrastructure — Cleanup Audit

**Date:** 2026-04-06  
**Status:** Completed

## Summary

Audit and cleanup of memory/KG-related projects in the workspace to eliminate redundancy, fix infrastructure issues, and prepare for domain-specific knowledge indexing via MCP.

---

## Issues Found & Fixed

### 1. Abandoned `lightrag-infrastructure/` Directory
- **Issue:** Empty directory at project root with only empty `config/`, `lib/`, `scripts/` subdirectories
- **Root cause:** LightRAG setup moved to `dva-kg-infrastructure/lightrag/` but old dir was left behind
- **Fix:** Deleted `lightrag-infrastructure/`
- **Impact:** LightRAG container was crash-looping because its volume mounts pointed to the deleted directory

### 2. LightRAG Container Crash-Loop
- **Issue:** `dva-lightrag` container failing with `can't open file '/app/scripts/server.py'`
- **Root cause:** Container was started from old `lightrag-infrastructure/` compose file, volume mounts pointed to empty dirs
- **Fix:** Stopped old container, restarted from `dva-kg-infrastructure/lightrag/docker-compose.yml`
- **Status:** Container now healthy on port 8001

### 3. Isolated Docker Networks (3 separate `dva-network` bridges)
- **Issue:** Three separate Docker networks instead of one shared network:
  - `dva-network` (shared, used by kg-mcp and mcp-servers)
  - `lightrag-infrastructure_dva-network` (orphaned)
  - `neo4j-infrastructure_dva-network` (isolated — Neo4j was unreachable from other services)
- **Root cause:** Each docker-compose.yml defined `dva-network` as `driver: bridge` instead of `external: true`
- **Fix:**
  - Changed `dva-kg-infrastructure/lightrag/docker-compose.yml` network to `external: true`
  - Changed `dva-kg-infrastructure/neo4j/docker-compose.yml` network to `external: true`
  - Connected `dva-neo4j` container to shared `dva-network`
  - Removed orphaned networks
- **Status:** Single `dva-network` now shared by all services

### 4. Neo4j Namespace Collision (Entity label)
- **Issue:** Both `neo4j-agent-memory` (memory-mcp) and `dva kg ingest` create nodes with `Entity` label in the same Neo4j instance
- **Memory-mcp labels:** `Conversation`, `Message`, `Entity`, `Preference`, `Fact`, `ReasoningTrace`, `ReasoningStep`, `Tool`, `ToolCall`
- **KG ingest labels:** Dynamic from LLM (`Patient`, `Facility`, etc.), `Code::*` for git repos, `Document`, falls back to `Entity`
- **Fixes applied:**
  - `entity_extraction.py`: Default entity type changed from `Entity` → `KGEntity`
  - `neo4j_client.py`: `sanitize_label()` fallback changed from `Entity` → `KGEntity`
  - `ingest.py`: Added `_source: "dva_kg"` property to all ingested nodes
  - `neo4j_client.py`: `get_stats()` queries scoped to `WHERE n._source = 'dva_kg'`
  - `neo4j_client.py`: Vector index renamed from `entity_embeddings` → `kg_entity_embeddings` on `KGEntity` label
  - `search.py`: Exact search scoped to `WHERE n._source = 'dva_kg'`
  - `query.py`: All simple Cypher patterns scoped to `WHERE n._source = 'dva_kg'`
  - `query.py`: Vertex AI prompt updated to always include `_source` filter
  - **CRITICAL:** `kg.py` clear command changed from `MATCH (n) DETACH DELETE n` to `MATCH (n) WHERE n._source = 'dva_kg' DETACH DELETE n` — prevents accidental deletion of memory-mcp data

### 5. kg-mcp Not Standard MCP (Assessment Only)
- **Issue:** `dva-kg-infrastructure/kg-mcp/` uses custom FastAPI HTTP endpoints, NOT MCP SSE/stdio transport
- **Impact:** Cannot be used by Windsurf, Claude Desktop, or the mcp-gateway
- **Current state:** Running on port 8125, functional but isolated
- **Recommendation:** Rebuild as proper FastMCP SSE server in `dva-mcp-servers/kg/` (Phase 1 task)
- **No code change made** — this is a build task, not a cleanup task

---

## Files Modified

| File | Change |
|------|--------|
| `dva-kg-infrastructure/lightrag/docker-compose.yml` | Network → `external: true` |
| `dva-kg-infrastructure/neo4j/docker-compose.yml` | Network → `external: true` |
| `dva-agentic-cli/.../kg/entity_extraction.py` | Default type `Entity` → `KGEntity` |
| `dva-agentic-cli/.../kg/neo4j_client.py` | `sanitize_label` fallback, scoped `get_stats`, renamed vector index |
| `dva-agentic-cli/.../kg/ingest.py` | Added `_source: "dva_kg"` to all nodes |
| `dva-agentic-cli/.../kg/search.py` | Scoped exact search to `_source = 'dva_kg'` |
| `dva-agentic-cli/.../kg/query.py` | Scoped all Cypher patterns + Vertex AI prompt |
| `dva-agentic-cli/.../commands/kg.py` | Scoped `clear` command to `_source = 'dva_kg'` |

## Files/Dirs Deleted

| Path | Reason |
|------|--------|
| `lightrag-infrastructure/` | Abandoned empty directory, real LightRAG at `dva-kg-infrastructure/lightrag/` |

## Docker Changes

| Action | Detail |
|--------|--------|
| Removed `lightrag-infrastructure_dva-network` | Orphaned network |
| Removed `neo4j-infrastructure_dva-network` | Isolated network, Neo4j moved to shared |
| Reconnected `dva-neo4j` to `dva-network` | Was on isolated network |
| Restarted `dva-lightrag` from correct compose | Now mounts correct `scripts/server.py` |

---

## Current Docker State (Post-Cleanup)

```
CONTAINER          PORT    STATUS    NETWORK
dva-neo4j          7687    healthy   dva-network
dva-lightrag       8001    healthy   dva-network
dva-kg-mcp         8125    healthy   dva-network
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
| `KGEntity` | dva kg | Default fallback for extracted entities |
| `Patient` | dva kg | Domain entity (from LLM extraction) |
| `Facility` | dva kg | Domain entity (from LLM extraction) |
| `Code::*` | dva kg | Code entities (git repos) |
| `Document` | dva kg | Raw documents (no extraction) |

**Disambiguation:** All dva kg nodes have `_source: "dva_kg"` property.

---

## Next Steps (Not Part of Cleanup)

1. **Phase 1:** Build proper kg-mcp with FastMCP SSE in `dva-mcp-servers/kg/`, wire into gateway
2. **Phase 2:** Index business requirements using `dva kg ingest` + LightRAG workspaces
3. **Phase 3:** Link `dva code onboard` to KG workspaces for per-project context
4. **Phase 4:** Configure coding tools to use gateway for business requirements context via MCP
