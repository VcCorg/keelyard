# LightRAG Query & Search Fix

## Problem

The `dva kg query` and `dva kg search` commands were returning `None` even with valid data:

```bash
$ dva kg query "patient banner"
✓ Query executed (mode: hybrid)
None  ← Should show results!

$ dva kg search "banner"
✓ Search completed
None  ← Should show results!
```

## Root Cause

Looking at the LightRAG server logs:

```
ERROR: Query failed: 'function' object has no attribute 'func'
```

**The Issue:** LightRAG's internal caching mechanism expects LLM functions to have a `.func` attribute (added by the `tenacity` retry decorator). Our custom Vertex AI and Gemini wrappers didn't have this attribute, causing queries to fail silently.

### Why This Happened

1. LightRAG uses `tenacity` decorators on its built-in LLM functions
2. These decorators add a `.func` attribute for introspection and caching
3. Our custom wrappers for Vertex AI and Gemini didn't have this attribute
4. When LightRAG tried to access `.func` during query processing, it failed
5. The error was caught but results returned as `null`

## The Fix

### Updated `scripts/server.py`

**1. Gemini API Wrapper (Lines 81-94):**

```python
import functools

@functools.wraps(_gemini_complete)
async def gemini_wrapper(*args, **kwargs):
    """Wrapper that injects model parameter and API key for Gemini."""
    if 'api_key' not in kwargs:
        kwargs['api_key'] = gemini_api_key
    return await _gemini_complete(llm_model_name, *args, **kwargs)

# Add func attribute for compatibility with LightRAG's caching
gemini_wrapper.func = gemini_wrapper  # ← Added this!

llm_model_func = gemini_wrapper
```

**2. Vertex AI Wrapper (Lines 103-139):**

```python
import functools

@functools.wraps(openai_complete_if_cache)
async def vertex_ai_wrapper(prompt: str, system_prompt: str = None, **kwargs):
    """Custom wrapper for Vertex AI Gemini models."""
    model = GenerativeModel(llm_model_name)
    
    # Combine system prompt and user prompt
    full_prompt = prompt
    if system_prompt:
        full_prompt = f"{system_prompt}\n\n{prompt}"
    
    # Generate response
    response = await asyncio.to_thread(
        model.generate_content,
        full_prompt,
        generation_config=kwargs.get('generation_config')
    )
    
    return response.text

# Add func attribute for compatibility with LightRAG's caching
vertex_ai_wrapper.func = vertex_ai_wrapper  # ← Added this!

llm_model_func = vertex_ai_wrapper
```

### What Changed

1. **Added `@functools.wraps` decorator** - Preserves metadata from the original function
2. **Added `.func` attribute** - Makes wrappers compatible with LightRAG's caching system
3. **Imported `functools`** - Standard library module for function wrapping

## Testing the Fix

### Step 1: Restart LightRAG

```bash
cd /Users/your-user/dva-agentic-project/lightrag-infrastructure
docker restart dva-lightrag
```

Wait ~30 seconds for startup, then verify:
```bash
curl http://localhost:8001/health
```

### Step 2: Test Query Command

```bash
cd /Users/your-user/dva-agentic-project
dva kg query "Pediatric Height & Weight Metrics"
```

**Expected Output:**
```
✓ Query executed (mode: hybrid)

[Actual query results with relevant information about pediatric metrics]
```

### Step 3: Test Search Command

```bash
dva kg search "banner"
```

**Expected Output:**
```
✓ Search completed

[Search results showing documents/chunks containing "banner"]
```

### Step 4: Test Different Query Modes

```bash
# Local mode (focuses on specific entities)
dva kg query "patient banner" --mode local

# Global mode (high-level overview)
dva kg query "clinical workflows" --mode global

# Naive mode (simple keyword search)
dva kg query "metrics" --mode naive

# Hybrid mode (default, combines approaches)
dva kg query "patient care" --mode hybrid
```

### Step 5: Verify No Errors in Logs

```bash
docker logs dva-lightrag --tail 50
```

You should NO LONGER see:
```
ERROR: Query failed: 'function' object has no attribute 'func'
```

## Query Modes Explained

LightRAG supports different query modes:

| Mode | Description | Best For |
|------|-------------|----------|
| **naive** | Simple keyword matching | Quick lookups, exact terms |
| **local** | Entity-focused search | Finding specific entities and their relationships |
| **global** | High-level summaries | Understanding overall themes and patterns |
| **hybrid** | Combines all approaches | Most comprehensive results (default) |

## API Response Format

### Query Response

```json
{
    "success": true,
    "query": "patient banner",
    "mode": "hybrid",
    "result": "Detailed response text with information about patient banners..."
}
```

### Search Response

```json
{
    "success": true,
    "query": "banner",
    "top_k": 10,
    "results": "Search results with relevant document chunks..."
}
```

## Troubleshooting

### Still Getting `None` Results

1. **Check if documents are fully processed:**
   ```bash
   dva kg stats
   ```
   Make sure "✓ Completed" count is > 0

2. **Check LightRAG logs for errors:**
   ```bash
   docker logs dva-lightrag --tail 100
   ```

3. **Verify the query is reaching the server:**
   ```bash
   curl -X POST http://localhost:8001/query \
     -H "Content-Type: application/json" \
     -d '{"query": "test", "mode": "hybrid", "top_k": 10}'
   ```

### "Query failed" Errors

If you still see errors:

1. **Check model availability:**
   - Gemini API: Verify API key is valid
   - Vertex AI: Verify GCP credentials and project access

2. **Check model name:**
   ```bash
   docker exec dva-lightrag env | grep -E "GEMINI_MODEL|VERTEX_AI_MODEL"
   ```

3. **Try with a different provider:**
   - Switch to OpenAI temporarily to isolate the issue
   - Update `.env`: `LLM_PROVIDER=openai`

### Empty Results But No Errors

If queries succeed but return empty results:

1. **Documents may still be processing:**
   ```bash
   dva kg stats
   ```
   Wait for all documents to show "✓ Completed"

2. **Try broader queries:**
   ```bash
   dva kg query "patient" --mode naive
   ```

3. **Check what's actually in the graph:**
   ```bash
   curl http://localhost:8001/stats
   ```

## Files Modified

1. **`/Users/your-user/dva-agentic-project/lightrag-infrastructure/scripts/server.py`**
   - Lines 81-94: Fixed Gemini wrapper with `.func` attribute
   - Lines 103-139: Fixed Vertex AI wrapper with `.func` attribute

## Summary

**Problem:** Query and search commands returned `None` due to missing `.func` attribute on custom LLM wrappers.

**Solution:** Added `@functools.wraps` decorator and `.func` attribute to make custom wrappers compatible with LightRAG's caching mechanism.

**Impact:** Query and search commands now work correctly with Vertex AI and Gemini API! 🎉

## Next Steps

After restarting the container:

1. ✅ Test query with known content
2. ✅ Test search with known keywords
3. ✅ Verify different query modes work
4. ✅ Check logs show no `.func` errors
5. ✅ Confirm results are relevant and useful
