---
description: Use graphify knowledge graph for codebase questions and architecture context
---

# Graphify Knowledge Graph Workflow

This project has a graphify knowledge graph at `graphify-out/`.

## When to Use Graphify

For codebase or architecture questions, when `graphify-out/graph.json` exists:

1. **First try graphify queries** - These return a scoped subgraph, usually much smaller than raw grep output:
   - `graphify query "<question>"` - BFS traversal of the graph for a question
   - `graphify path "<A>" "<B>"` - Shortest path between two nodes
   - `graphify explain "<concept>"` - Plain-language explanation of a node and its neighbors

2. **Check the wiki** - If `graphify-out/wiki/index.md` exists, navigate it instead of reading raw files

3. **Read the report** - Use `graphify-out/GRAPH_REPORT.md` only for broad architecture review or when query/path/explain do not surface enough context

## Keeping the Graph Current

After modifying code files in this session, run:
```bash
graphify update .
```

This updates the graph using AST-only extraction (no API cost).

## Graphify Commands Reference

- `graphify update <path> --force` - Re-extract code files and update the graph
- `graphify query "<question>"` - BFS traversal of graph.json for a question
- `graphify path "A" "B"` - Shortest path between two nodes in graph.json
- `graphify explain "X"` - Plain-language explanation of a node and its neighbors
- `graphify tree` - Emit a D3 v7 collapsible-tree HTML for graph.json

## Output Files

- `graphify-out/graph.json` - The code structure graph
- `graphify-out/GRAPH_REPORT.md` - Broad architecture report
- `graphify-out/wiki/index.md` - Navigable wiki (if generated)
- `graphify-out/manifest.json` - File metadata and hashes
