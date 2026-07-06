# Google Vertex AI Setup Guide

This guide explains how to set up and use Google Vertex AI with the Agentic CLI.

## Prerequisites

1. **Google Cloud Account**: You need an active Google Cloud account
2. **Google Cloud Project**: Create or have access to a GCP project
3. **Vertex AI API**: Enable the Vertex AI API in your project
4. **gcloud CLI** (optional but recommended): Install from https://cloud.google.com/sdk/docs/install

## Setup Methods

### Method 1: Using Application Default Credentials (Recommended)

This method uses your Google Cloud user credentials.

```bash
# 1. Install gcloud CLI (if not already installed)
# Follow: https://cloud.google.com/sdk/docs/install

# 2. Set your project
gcloud config set project YOUR_PROJECT_ID

# 3. Initialize KEEL with your project (automatically runs gcloud auth)
`agent init vertex-ai --project-id YOUR_PROJECT_ID --location us-central1

# If already authenticated, skip the auth step
`agent init vertex-ai --project-id YOUR_PROJECT_ID --location us-central1 --skip-auth
```

### Method 2: Using Service Account Key

This method uses a service account JSON key file.

```bash
# 1. Create a service account in Google Cloud Console
# 2. Grant it "Vertex AI User" role
# 3. Download the JSON key file

# 4. Initialize KEEL with the key file
`agent init vertex-ai \
  --project-id YOUR_PROJECT_ID \
  --location us-central1 \
  --credentials /path/to/service-account-key.json
```

## Initialize Vertex AI Configuration

The `keel init vertex-ai` command saves your Vertex AI settings for use in new projects. It automatically reuses existing configuration if available.

### Basic Usage

```bash
# First time: prompts for project ID and runs gcloud auth
`agent init vertex-ai

# Subsequent runs: reuses existing config, only runs auth
`agent init vertex-ai

# Update specific settings while keeping others
`agent init vertex-ai --location us-east1

# With all options
`agent init vertex-ai \
  --project-id my-gcp-project \
  --location us-central1 \
  --model gemini-pro \
  --credentials /path/to/key.json

# Skip authentication if already authenticated
`agent init vertex-ai --skip-auth
```

### Options

All options are optional. If not provided, existing values are reused:

- `--project-id`: Your Google Cloud Project ID (prompts if no existing config)
- `--location`: Google Cloud region (default: existing or us-central1)
- `--model`: Vertex AI model to use (default: existing or gemini-pro)
- `--credentials`: Path to service account JSON key file (optional)
- `--skip-auth`: Skip automatic gcloud auth application-default login

### Available Models

- `gemini-pro`: Text generation
- `gemini-pro-vision`: Multimodal (text and images)
- `gemini-1.5-pro`: Latest Gemini model
- `gemini-1.5-flash`: Faster, more efficient model

## View Current Configuration

```bash
# Show saved configuration
`agent init show

# Output:
# Vertex AI:
#   Project ID: my-gcp-project
#   Location: us-central1
#   Model: gemini-pro
#   Credentials: Application Default
```

## Create a Project with Vertex AI

Once initialized, new projects will automatically use your Vertex AI configuration:

```bash
# Create a new project
`agent project create my-vertex-project

# The .env file will be pre-configured with:
# GOOGLE_PROJECT_ID=my-gcp-project
# GOOGLE_LOCATION=us-central1
# VERTEX_AI_MODEL=gemini-pro
# AGENT_PROVIDER=vertex_ai
```

## Using Vertex AI in Your Project

### Install Vertex AI Dependencies

```bash
cd my-vertex-project
uv venv
source .venv/bin/activate
uv pip install -e ".[dev,vertex_ai]"
```

### Using the Vertex AI Agent

```python
from src.agents.vertex_ai_agent import VertexAIAgent
from src.config import settings

# Create a Vertex AI agent
agent = VertexAIAgent(
    project_id=settings.google_project_id,
    location=settings.google_location,
    model=settings.vertex_ai_model,
    credentials_path=settings.google_application_credentials,
)

# Use the agent
result = await agent.process({"text": "Hello, Vertex AI!"})
print(result["result"])
```

### Configuration via Environment Variables

Your `.env` file contains:

```bash
# Google Vertex AI Configuration
GOOGLE_PROJECT_ID=your-project-id
GOOGLE_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json  # Optional
VERTEX_AI_MODEL=gemini-pro

# Agent Configuration
AGENT_PROVIDER=vertex_ai  # Use Vertex AI as the provider
```

## Troubleshooting

### Authentication Errors

**Problem**: `google.auth.exceptions.DefaultCredentialsError`

**Solution**:
```bash
# Run authentication
gcloud auth application-default login

# Or set credentials path
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

### API Not Enabled

**Problem**: `Vertex AI API has not been used in project`

**Solution**:
```bash
# Enable the API
gcloud services enable aiplatform.googleapis.com --project=YOUR_PROJECT_ID
```

### Permission Denied

**Problem**: `Permission denied on resource project`

**Solution**:
- Ensure your account has the "Vertex AI User" role
- Grant the role in Cloud Console: IAM & Admin → IAM → Add Role

### Model Not Found

**Problem**: `Model not found: gemini-pro`

**Solution**:
- Check available models in your region
- Some models may not be available in all regions
- Try `us-central1` or `us-east1`

## Regions and Availability

### Recommended Regions

- `us-central1` (Iowa) - Best availability
- `us-east1` (South Carolina)
- `europe-west1` (Belgium)
- `asia-southeast1` (Singapore)

### Check Model Availability

```bash
# List available models
gcloud ai models list --region=us-central1
```

## Cost Considerations

Vertex AI charges based on:
- **Input tokens**: Text sent to the model
- **Output tokens**: Text generated by the model
- **Model type**: Different models have different pricing

### Pricing (approximate)

- Gemini Pro: ~$0.00025 per 1K characters
- Gemini Pro Vision: ~$0.0025 per image

Check current pricing: https://cloud.google.com/vertex-ai/pricing

## Best Practices

1. **Use Application Default Credentials** for development
2. **Use Service Accounts** for production
3. **Set appropriate IAM roles** (least privilege)
4. **Monitor usage** in Cloud Console
5. **Set up billing alerts** to avoid surprises
6. **Use `.gitignore`** for credential files
7. **Rotate service account keys** regularly

## Security

### Never Commit Credentials

Add to `.gitignore`:
```
.env
*.json  # Service account keys
.keel-agentic/config.json
```

### Secure Service Account Keys

```bash
# Set restrictive permissions
chmod 600 /path/to/service-account-key.json

# Store in secure location
mv key.json ~/.gcp/my-project-key.json
```

## Advanced Configuration

### Multiple Projects

```bash
# Initialize different projects
`agent init vertex-ai --project-id project-dev
# Work with dev project...

`agent init vertex-ai --project-id project-prod
# Work with prod project...
```

### Custom Endpoints

Set in `.env`:
```bash
# Use a different endpoint (rare)
VERTEX_AI_ENDPOINT=https://custom-endpoint.googleapis.com
```

## Resources

- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Gemini API Documentation](https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/gemini)
- [Google Cloud SDK](https://cloud.google.com/sdk/docs)
- [Service Accounts](https://cloud.google.com/iam/docs/service-accounts)

## Support

For issues:
1. Check this guide
2. Review error messages
3. Check Google Cloud Console logs
4. Verify API is enabled
5. Confirm IAM permissions

---

**Quick Start Summary**

```bash
# 1. Initialize (automatically runs gcloud auth)
`agent init vertex-ai --project-id YOUR_PROJECT_ID

# 2. Create project
`agent project create my-ai-project

# 4. Install and run
cd my-ai-project
uv venv && source .venv/bin/activate
uv pip install -e ".[dev,vertex_ai]"
python src/main.py
```
