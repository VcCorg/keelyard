# Quick Fix for API Key Error

## The Problem
```
API key not valid. Please pass a valid API key.
```

## The Cause
LightRAG was trying to use **Gemini API** with **Vertex AI credentials**, which don't work together.

## Quick Solution (Choose One)

### Option A: Use Vertex AI (Your Current Setup)

Since you already have `LLM_PROVIDER=vertex_ai` configured, just restart:

```bash
cd /Users/your-user/agentic-project/lightrag-infrastructure
make restart
```

**What changed:**
- Fixed the code to properly use Vertex AI SDK instead of Gemini API
- Fixed model name from `gemini-3-pro-preview` to `gemini-1.5-flash`

**Verify it works:**
```bash
# Check logs
make logs

# Should see: "Using Vertex AI LLM: gemini-1.5-flash"
```

---

### Option B: Switch to Gemini API (Simpler)

If Vertex AI doesn't work, switch to Gemini API:

1. **Get API Key:** https://makersuite.google.com/app/apikey

2. **Update `.env`:**
   ```bash
   # Comment out Vertex AI
   #LLM_PROVIDER=vertex_ai
   #GOOGLE_PROJECT_ID=ai-mkt-pl-np-20250916-oxlk
   
   # Use Gemini API instead
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=your_api_key_here
   GEMINI_MODEL=gemini-1.5-flash
   
   # Keep embeddings as OpenAI or switch to Vertex AI
   EMBEDDING_PROVIDER=openai
   OPENAI_API_KEY=your_openai_key_here
   ```

3. **Restart:**
   ```bash
   make restart
   ```

---

## Test It

```bash
# Insert test document
curl -X POST http://localhost:8001/insert \
  -H "Content-Type: application/json" \
  -d '{"text": "Test document about AI and machine learning."}'

# Check status
curl http://localhost:8001/document-status
```

If you see `"completed": 1` without errors, it's working! ✅

---

## Still Not Working?

Check the logs:
```bash
make logs
```

Look for:
- ✅ `"Using Vertex AI LLM: gemini-1.5-flash"` (if using Vertex AI)
- ✅ `"Using Gemini API LLM: gemini-1.5-flash"` (if using Gemini API)
- ❌ Any error messages about API keys or authentication

See `GOOGLE_AUTH_FIX.md` for detailed troubleshooting.
