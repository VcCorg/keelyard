# KG Linker LightRAG Integration

## Overview

The KG Linker now integrates with LightRAG for hybrid semantic search + LLM evaluation when linking Code entities to Document nodes.

## Architecture

### New Flow (with LightRAG enabled)
```
1. Pull Code entities from Neo4j
2. Pull Business docs from Neo4j
3. Ingest both into LightRAG for semantic embeddings
4. Query LightRAG for semantic similarity (code ↔ docs)
5. Batch evaluate with Vertex AI LLM
6. Combine LightRAG similarity scores + LLM evaluation
7. Write typed edges to Neo4j
```

### Fallback (LightRAG unavailable or disabled)
```
1. Pull Code entities from Neo4j
2. Pull Business docs from Neo4j
3. Batch evaluate with Vertex AI LLM
4. Write typed edges to Neo4j
```

## Hybrid Confidence Scoring

When LightRAG is available, confidence scores are calculated as:

```
combined_confidence = (lightrag_weight * lightrag_score) + ((1 - lightrag_weight) * llm_score)
```

- **Default lightrag_weight**: 0.6 (60% LightRAG, 40% LLM)
- **Range**: 0.0-1.0
- **Adjustable**: Via `--lightrag-weight` flag

## Usage

### Enable LightRAG (default)
```bash
keel kg link --domain cwow-facility --dry-run
keel kg link --domain cwow-facility
```

### Disable LightRAG (LLM-only mode)
```bash
keel kg link --domain cwow-facility --dry-run --no-lightrag
```

### Adjust LightRAG weight
```bash
keel kg link --domain cwow-facility --lightrag-weight 0.7  # 70% LightRAG, 30% LLM
```

## Requirements

- LightRAG service running on `http://localhost:8001` (configurable via KG config)
- Neo4j configured and running
- Vertex AI configured for LLM evaluation

## Graceful Degradation

If LightRAG service is unavailable:
- Logs warning and falls back to LLM-only mode
- Continues operation without interruption
- No manual intervention required

## Implementation Details

### Files Modified
- `agentic_cli/src/agentic_cli/kg/linker.py`
  - Added `_get_lightrag_client()` method
  - Added `_ingest_to_lightrag()` method
  - Added `_query_lightrag_similarity()` method
  - Updated `_evaluate_batch()` to combine scores
  - Updated `run()` to ingest before evaluation
  - Added `use_lightrag` and `lightrag_weight` parameters

- `agentic-cli/src/agentic_cli/commands/kg.py`
  - Added `--lightrag/--no-lightrag` flag
  - Added `--lightrag-weight` flag
  - Updated help text

### Key Methods

**_ingest_to_lightrag()**
- Ingests CodeEntity or BusinessDoc objects into LightRAG
- Builds formatted text with metadata
- Handles errors gracefully

**_query_lightrag_similarity()**
- Queries LightRAG for semantic similarity between code and docs
- Returns dict mapping doc_id to similarity score (0.0-1.0)
- Uses LightRAG search API

**_evaluate_batch()**
- Gets LightRAG similarity scores if configured
- Combines with LLM confidence scores
- Applies weighted average for hybrid scoring
- Logs debug info for score breakdown

## Testing

### Test Results
- ✅ LightRAG enabled, service down: Graceful fallback to LLM-only
- ✅ LightRAG disabled (--no-lightrag): LLM-only mode works
- ✅ cwow-facility domain: 4 candidates found in both modes

### To Test with LightRAG Running
```bash
# Start LightRAG service
cd kg-infrastructure/lightrag && docker-compose up -d

# Run linker with LightRAG
keel kg link --domain cwow-facility --dry-run --lightrag
```

## Benefits

1. **Semantic Understanding**: Leverages embeddings for semantic similarity beyond keyword matching
2. **Improved Accuracy**: Hybrid scoring reduces false positives/negatives
3. **Graceful Fallback**: Works even when LightRAG is unavailable
4. **Configurable**: Adjust weight based on domain needs
5. **Backward Compatible**: Existing workflows continue to work unchanged

## Future Enhancements

- Add LightRAG health check before ingestion
- Implement incremental ingestion (only new/changed entities)
- Add similarity score thresholds for LightRAG-only matching
- Support for custom embedding models
