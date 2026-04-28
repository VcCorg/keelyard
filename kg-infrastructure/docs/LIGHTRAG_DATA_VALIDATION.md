# LightRAG Data Validation Guide

## Current Status

### ✅ What's Working
- PDF content extraction (477,191 characters from 3 PDFs)
- File ingestion via DVA CLI
- LightRAG API endpoints (health, stats, insert)
- Container infrastructure

### ⚠️ Current Limitation
**LightRAG requires OpenAI API key for processing**

The documents are being extracted and sent to LightRAG, but they fail during processing because:
1. LightRAG uses OpenAI for embeddings and entity extraction
2. The current server implementation is hardcoded to use OpenAI
3. Vertex AI configuration in `.env` is not being used by LightRAG library

## How to Validate Data Ingestion

### 1. Check Document Status

```bash
# View document processing status
docker exec dva-lightrag cat /data/lightrag/kv_store_doc_status.json | python3 -m json.tool
```

**What to look for:**
- `status`: "completed" (success) or "failed" (error)
- `content_summary`: Shows extracted text from PDF
- `content_length`: Number of characters extracted
- `error_msg`: Error details if failed

### 2. Check Full Documents Store

```bash
# View stored documents
docker exec dva-lightrag cat /data/lightrag/kv_store_full_docs.json | python3 -m json.tool | head -100
```

**What to look for:**
- Document IDs and content
- Timestamps (create_time, update_time)
- Full document text

### 3. Check Data Files

```bash
# List all LightRAG data files
docker exec dva-lightrag ls -lh /data/lightrag/

# Expected files:
# - kv_store_doc_status.json (document processing status)
# - kv_store_full_docs.json (full document content)
# - graph_chunk_entity_relation.graphml (graph structure, if processing succeeded)
# - vdb_*.json (vector database files, if processing succeeded)
```

### 4. Check Container Logs

```bash
# View real-time logs
cd lightrag-infrastructure
make logs

# Or check recent logs
docker logs dva-lightrag --tail 50
```

**What to look for:**
- "Inserted document: X characters" (successful ingestion)
- "Insert error:" (processing errors)
- API key errors
- Processing status

## Current Data Status

### Ingested Data
```
✓ Successfully ingested directory
  Files: 3
  Total characters: 477,191
```

**Files:**
1. CWOW-235996 View and Update Clinical Details 17_Baseline 4.0.pdf (366,148 chars)
2. CWOW-226167 Display Patient Banner 10_Baseline 4.0.pdf (68,908 chars)
3. CWOW-244309 View Patient List 06_Baseline 4.0.pdf (42,128 chars)

### Processing Status
**Status:** ❌ Failed (OpenAI API key required)

**Error:**
```
Error code: 401 - You didn't provide an API key
```

**Content Extracted:** ✅ Yes
- All PDF content was successfully extracted
- Text is stored in `kv_store_full_docs.json`
- Content summaries are available

**Graph Created:** ❌ No
- Requires OpenAI API for entity extraction
- Requires OpenAI API for embeddings
- Graph files not created yet

## Solutions

### Option 1: Use OpenAI (Recommended for LightRAG)

1. **Get OpenAI API Key**
   - Visit: https://platform.openai.com/account/api-keys
   - Create a new API key

2. **Update Configuration**
   ```bash
   cd lightrag-infrastructure
   
   # Edit .env file
   nano .env
   
   # Uncomment and set:
   LLM_PROVIDER=openai
   OPENAI_API_KEY=your_api_key_here
   OPENAI_MODEL=gpt-4o-mini
   
   EMBEDDING_PROVIDER=openai
   EMBEDDING_MODEL=text-embedding-3-small
   ```

3. **Restart LightRAG**
   ```bash
   make stop
   make start
   make validate
   ```

4. **Re-ingest Data**
   ```bash
   dva kg ingest --source cwow-patient-docs
   ```

5. **Validate Processing**
   ```bash
   # Check status
   docker exec dva-lightrag cat /data/lightrag/kv_store_doc_status.json | python3 -m json.tool | grep "status"
   
   # Should show: "status": "completed"
   ```

### Option 2: Switch to Neo4j (Uses Vertex AI)

If you want to use Vertex AI (which you already have configured):

```bash
# 1. Start Neo4j
cd neo4j-infrastructure
make start
make validate

# 2. Configure DVA CLI
dva kg init --provider neo4j \
  --uri bolt://localhost:7687 \
  --username neo4j \
  --password password

# 3. Ingest data (will use Vertex AI for entity extraction)
dva kg ingest --source cwow-patient-docs \
  --extract-entities \
  --build-relationships

# 4. Validate
dva kg stats
dva kg query "What are the main topics?"
dva kg visualize
```

### Option 3: Update LightRAG Server (Advanced)

Update the server to support Vertex AI (requires code changes):

1. Modify `scripts/server.py` to support multiple LLM providers
2. Add Vertex AI initialization logic
3. Update LightRAG initialization to use provider-specific functions
4. Rebuild container

**This is a more complex solution and requires understanding of LightRAG internals.**

## Validation Checklist

### ✅ Ingestion Successful If:
- [x] Files show in DVA CLI output
- [x] Character count matches file sizes
- [x] `kv_store_full_docs.json` contains document content
- [x] `kv_store_doc_status.json` shows documents

### ✅ Processing Successful If:
- [ ] `status`: "completed" in doc_status.json
- [ ] `graph_chunk_entity_relation.graphml` file exists
- [ ] `vdb_entities.json`, `vdb_relationships.json`, `vdb_chunks.json` files exist
- [ ] `dva kg query` returns results
- [ ] `dva kg search` returns results

## Quick Validation Commands

```bash
# 1. Check if data was ingested
dva kg stats

# 2. Check document status
docker exec dva-lightrag cat /data/lightrag/kv_store_doc_status.json | python3 -m json.tool | grep -A 3 "status"

# 3. Check file sizes
docker exec dva-lightrag ls -lh /data/lightrag/

# 4. Try a query (will fail if processing failed)
dva kg query "What is this about?"

# 5. Check logs for errors
docker logs dva-lightrag --tail 30 | grep -i error
```

## Understanding the Data Flow

```
PDF Files
   ↓
DVA CLI (extract text with PyPDF2)
   ↓
LightRAG API (/insert endpoint)
   ↓
Store in kv_store_full_docs.json ✅ (This works)
   ↓
Process with LLM (OpenAI) ❌ (This fails - needs API key)
   ↓
Extract entities and relationships
   ↓
Create embeddings
   ↓
Store in graph and vector DB
   ↓
Ready for queries
```

**Current Status:** Stopped at "Process with LLM" step due to missing OpenAI API key.

## Recommendations

### For Production Use:

1. **Use Neo4j + Vertex AI**
   - You already have Vertex AI configured
   - More mature and feature-rich
   - Better for complex queries
   - Supports visualization

2. **Or: Add OpenAI API Key to LightRAG**
   - Simple setup
   - Fast ingestion
   - Good for RAG use cases
   - Cost: ~$0.01-0.10 per document

### For Development/Testing:

1. **Use Neo4j with local data**
   - No external API dependencies for basic operations
   - Full control over processing
   - Can use Vertex AI for entity extraction (optional)

## Summary

**Data Ingestion:** ✅ Working  
**Content Extraction:** ✅ Working (477,191 characters extracted)  
**Content Storage:** ✅ Working (stored in JSON files)  
**Graph Processing:** ❌ Blocked (needs OpenAI API key)  
**Query/Search:** ❌ Not available (graph not built)  

**Next Step:** Choose Option 1 (add OpenAI key) or Option 2 (switch to Neo4j) to complete the data processing pipeline.
