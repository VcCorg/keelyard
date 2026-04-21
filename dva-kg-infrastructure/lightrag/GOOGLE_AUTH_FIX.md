# Google Authentication Fix for LightRAG

## Problem Summary

The error `API key not valid. Please pass a valid API key` occurred because LightRAG was trying to use **Gemini API** (generativelanguage.googleapis.com) with Google Cloud Application Default Credentials (ADC), which are incompatible.

### Root Cause

**Two Different Google AI Services:**

1. **Gemini API** (`generativelanguage.googleapis.com`)
   - Requires: Gemini API key from Google AI Studio
   - Used by: LightRAG's `gemini_complete_if_cache` function
   - Best for: Development, simple projects

2. **Vertex AI** (`aiplatform.googleapis.com`)
   - Requires: Google Cloud credentials (ADC, service accounts)
   - Used by: Vertex AI SDK
   - Best for: Production, enterprise deployments

The original code tried to use Vertex AI credentials (access tokens) as Gemini API keys, which failed because they're different authentication systems.

## Solution

We've implemented support for **both** authentication methods. Choose the one that fits your needs:

---

## Option 1: Gemini API (Recommended for Quick Start)

### Step 1: Get Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated key

### Step 2: Update `.env` File

```bash
# Use Gemini API
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash

# For embeddings, you can use OpenAI or Vertex AI
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
EMBEDDING_MODEL=text-embedding-3-small
```

### Step 3: Restart LightRAG

```bash
cd /Users/your-user/dva-agentic-project/lightrag-infrastructure
make restart
```

### Pros & Cons

✅ **Pros:**
- Simple setup (just need API key)
- No GCP project required
- Free tier available
- Fast to get started

❌ **Cons:**
- API key management (less secure than ADC)
- Rate limits may be lower
- Not suitable for production at scale

---

## Option 2: Vertex AI (Recommended for Production)

### Step 1: Ensure GCP Setup

Make sure you have:
- A GCP project with Vertex AI API enabled
- Application Default Credentials configured:
  ```bash
  gcloud auth application-default login
  ```

### Step 2: Update `.env` File

```bash
# Use Vertex AI
LLM_PROVIDER=vertex_ai
GOOGLE_PROJECT_ID=your-gcp-project-id
GOOGLE_LOCATION=us-central1
VERTEX_AI_MODEL=gemini-1.5-flash

# Use Vertex AI embeddings
EMBEDDING_PROVIDER=vertex_ai
EMBEDDING_MODEL=text-embedding-005
```

### Step 3: Verify Credentials Mount

The docker-compose.yml mounts your GCP credentials:
```yaml
volumes:
  - ~/.config/gcloud:/root/.config/gcloud:ro
```

Make sure `~/.config/gcloud/application_default_credentials.json` exists.

### Step 4: Restart LightRAG

```bash
cd /Users/your-user/dva-agentic-project/lightrag-infrastructure
make restart
```

### Pros & Cons

✅ **Pros:**
- Secure (uses ADC, no API keys in code)
- Better for production
- Higher rate limits
- Enterprise features
- Integrated with GCP services

❌ **Cons:**
- Requires GCP project
- More complex setup
- May incur GCP costs

---

## What Was Fixed

### 1. Updated `.env.example`

Added clear distinction between Gemini API and Vertex AI:

```bash
# Alternative: Google Gemini API (simpler, requires API key from AI Studio)
# LLM_PROVIDER=gemini
# GEMINI_API_KEY=your_gemini_api_key_here
# GEMINI_MODEL=gemini-1.5-flash

# Alternative: Google Vertex AI (requires GCP credentials)
# LLM_PROVIDER=vertex_ai
# GOOGLE_PROJECT_ID=your-gcp-project-id
# GOOGLE_LOCATION=us-central1
# VERTEX_AI_MODEL=gemini-1.5-flash
```

### 2. Fixed `scripts/server.py`

**Before:** Tried to use ADC access tokens as Gemini API keys (failed)

**After:** Separated into two distinct implementations:

#### Gemini API Implementation (lines 65-88)
```python
if llm_provider == "gemini":
    # Uses GEMINI_API_KEY from environment
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not set...")
    
    async def gemini_wrapper(*args, **kwargs):
        kwargs['api_key'] = gemini_api_key
        return await _gemini_complete(llm_model_name, *args, **kwargs)
```

#### Vertex AI Implementation (lines 90-128)
```python
elif llm_provider == "vertex_ai":
    # Uses GCP credentials via ADC
    vertexai.init(project=project_id, location=location)
    
    async def vertex_ai_wrapper(prompt: str, system_prompt: str = None, **kwargs):
        model = GenerativeModel(llm_model_name)
        response = await asyncio.to_thread(
            model.generate_content,
            full_prompt,
            generation_config=kwargs.get('generation_config')
        )
        return response.text
```

### 3. Updated `docker-compose.yml`

Added GEMINI_API_KEY environment variable:
```yaml
- GEMINI_API_KEY=${GEMINI_API_KEY:-}
- GEMINI_MODEL=${GEMINI_MODEL:-gemini-1.5-flash}
```

---

## Verification

### Check Current Configuration

```bash
# View your current .env settings
cat /Users/your-user/dva-agentic-project/lightrag-infrastructure/.env | grep -E "(LLM_PROVIDER|GEMINI|VERTEX|GOOGLE)"
```

### Test the Fix

```bash
# Restart the service
cd /Users/your-user/dva-agentic-project/lightrag-infrastructure
make restart

# Check logs for successful initialization
make logs

# You should see:
# "Using Gemini API LLM: gemini-1.5-flash" (if using Gemini API)
# OR
# "Using Vertex AI LLM: gemini-1.5-flash (project: ..., location: ...)" (if using Vertex AI)
```

### Test with a Document

```bash
# Insert a test document
curl -X POST http://localhost:8001/insert \
  -H "Content-Type: application/json" \
  -d '{"text": "This is a test document about artificial intelligence."}'

# Check document status
curl http://localhost:8001/document-status
```

If successful, you should see the document processing without API key errors.

---

## Current Configuration

Your current `.env` file shows:
```bash
LLM_PROVIDER=vertex_ai
GOOGLE_PROJECT_ID=ai-mkt-pl-np-20250916-oxlk
VERTEX_AI_MODEL=gemini-3-pro-preview
```

### Recommended Next Steps

**If you want to use Vertex AI (current setup):**
1. Verify your GCP credentials are working:
   ```bash
   gcloud auth application-default print-access-token
   ```
2. Make sure Vertex AI API is enabled in your project
3. Restart the service: `make restart`

**If you want to switch to Gemini API (simpler):**
1. Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Update `.env`:
   ```bash
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=your_api_key_here
   GEMINI_MODEL=gemini-1.5-flash
   ```
3. Restart: `make restart`

---

## Troubleshooting

### "GEMINI_API_KEY not set" Error

**Solution:** Add the API key to your `.env` file:
```bash
GEMINI_API_KEY=your_actual_api_key_here
```

### "GOOGLE_PROJECT_ID not set for Vertex AI" Error

**Solution:** Add your GCP project ID to `.env`:
```bash
GOOGLE_PROJECT_ID=your-gcp-project-id
```

### "Could not get Google Cloud credentials" Warning

**Solution:** Run:
```bash
gcloud auth application-default login
```

### Still Getting API Key Errors

1. Check which provider is active:
   ```bash
   docker exec dva-lightrag env | grep LLM_PROVIDER
   ```

2. Verify the API key/credentials are set:
   ```bash
   # For Gemini API
   docker exec dva-lightrag env | grep GEMINI_API_KEY
   
   # For Vertex AI
   docker exec dva-lightrag env | grep GOOGLE_PROJECT_ID
   ```

3. Check logs for detailed error messages:
   ```bash
   make logs
   ```

---

## Summary

The fix separates **Gemini API** (requires API key) from **Vertex AI** (requires GCP credentials) into two distinct code paths. Choose the authentication method that fits your use case:

- **Development/Testing:** Use Gemini API (simpler)
- **Production:** Use Vertex AI (more secure, scalable)

Both methods now work correctly with LightRAG! 🎉
