# Confluence Integration Setup

This guide explains how to configure Confluence integration for the DVA Agentic CLI knowledge graph feature.

## Prerequisites

- Confluence Cloud or Server instance
- Confluence account with read access to the pages/spaces you want to ingest
- API token (for Confluence Cloud) or password (for Confluence Server)

## Getting an API Token

### For Confluence Cloud

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **"Create API token"**
3. Give it a name (e.g., "DVA CLI")
4. Copy the token (you won't be able to see it again!)

### For Confluence Server

Use your regular Confluence password.

## Configuration

### Option 1: Configure via CLI

```bash
dva kg init \
  --confluence-url https://confluence.company.com \
  --confluence-username your.email@company.com \
  --confluence-token YOUR_API_TOKEN
```

### Option 2: Configure Separately

```bash
# First configure Neo4j and embeddings
dva kg init --provider neo4j --uri bolt://localhost:7687

# Then add Confluence credentials
dva kg init \
  --confluence-url https://confluence.example.com \
  --confluence-username your.email@example.com \
  --confluence-token YOUR_API_TOKEN
```

## Verify Configuration

```bash
dva kg config --show
```

You should see:
```
         Knowledge Graph Configuration         
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Setting             ┃ Value                             ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Provider            │ neo4j                             │
│ Neo4j URI           │ bolt://localhost:7687             │
│ Neo4j Username      │ neo4j                             │
│ Neo4j Password      │ ***                               │
│ Embeddings Provider │ vertex-ai                         │
│ Confluence URL      │ https://confluence.example.com     │
│ Confluence Username │ your.email@example.com             │
│ Confluence Token    │ ***                               │
└─────────────────────┴───────────────────────────────────┘
```

## Usage

### Ingest a Single Page

```bash
dva kg ingest https://confluence.example.com/pages/177118522/APOC+Knowledge+Base
```

### Ingest an Entire Space

```bash
dva kg ingest https://confluence.example.com/spaces/CWHE
```

### With Entity Extraction

```bash
dva kg ingest https://confluence.example.com/pages/177118522/APOC+Knowledge+Base \
  --extract-entities \
  --build-relationships
```

## Supported URL Formats

### Page URL
```
https://confluence.company.com/pages/123456/Page+Title
https://confluence.company.com/display/SPACE/Page+Title
```

### Space URL
```
https://confluence.company.com/spaces/SPACEKEY
https://confluence.company.com/display/SPACEKEY
```

## Troubleshooting

### Authentication Failed

**Error**: `401 Unauthorized` or `Authentication failed`

**Solutions**:
1. Verify your API token is correct
2. For Confluence Cloud, make sure you're using your **email** as the username, not your username
3. Check that the API token hasn't expired
4. Regenerate the API token if needed

### Page Not Found

**Error**: `404 Not Found`

**Solutions**:
1. Verify the page ID in the URL is correct
2. Check that you have permission to view the page
3. Make sure the page hasn't been deleted or moved

### Rate Limiting

**Error**: `429 Too Many Requests`

**Solutions**:
1. Wait a few minutes before trying again
2. Reduce the number of pages you're ingesting at once
3. Contact your Confluence administrator about rate limits

### SSL Certificate Errors

**Error**: `SSL: CERTIFICATE_VERIFY_FAILED`

**Solutions**:
1. For Confluence Server with self-signed certificates, you may need to configure SSL verification
2. Contact your IT department for the proper certificate

## Security Best Practices

1. **Never commit API tokens to version control**
2. **Use API tokens instead of passwords** (for Confluence Cloud)
3. **Rotate API tokens regularly**
4. **Use tokens with minimal required permissions**
5. **Store tokens securely** (they're stored in `~/.dva-agentic/kg-config.json`)

## Configuration File Location

Confluence credentials are stored in:
```
~/.dva-agentic/kg-config.json
```

This file contains sensitive information and should be protected.

## Permissions Required

The Confluence account needs:
- **Read** access to the pages/spaces you want to ingest
- For Cloud: API token with appropriate scopes
- For Server: Regular user account with read permissions

## Examples

### Basic Ingestion
```bash
# Configure once
dva kg init \
  --confluence-url https://confluence.example.com \
  --confluence-username john.doe@example.com \
  --confluence-token abc123...

# Ingest pages
dva kg ingest https://confluence.example.com/pages/177118522/APOC+Knowledge+Base
dva kg ingest https://confluence.example.com/spaces/CWHE
```

### With Full Knowledge Graph Features
```bash
# Ingest with entity extraction and relationship building
dva kg ingest https://confluence.example.com/pages/177118522/APOC+Knowledge+Base \
  --extract-entities \
  --build-relationships

# Query the ingested data
dva kg query "Find all concepts related to APOC"

# Search semantically
dva kg search "knowledge base" --semantic

# Visualize
dva kg visualize --output confluence-graph.html
```

## Advanced Configuration

### Confluence Server (On-Premise)

For Confluence Server installations:

```bash
dva kg init \
  --confluence-url https://confluence-server.company.local \
  --confluence-username your_username \
  --confluence-token your_password
```

Note: The parser defaults to `cloud=True`. For Server installations, you may need to modify the parser code to set `cloud=False`.

### Custom Base URL

If your Confluence instance uses a custom base URL:

```bash
dva kg init \
  --confluence-url https://wiki.company.com \
  --confluence-username your.email@company.com \
  --confluence-token YOUR_API_TOKEN
```

## Next Steps

After configuring Confluence:

1. **Test the connection**: Try ingesting a single page first
2. **Configure Vertex AI**: For entity extraction, configure Vertex AI
3. **Start ingesting**: Ingest your knowledge base pages
4. **Query and search**: Use the knowledge graph features
5. **Generate tools**: Create ADK tools for your agents

## Support

For issues or questions:
1. Check the error message for specific guidance
2. Verify your configuration with `dva kg config --show`
3. Test with a simple page first before ingesting entire spaces
4. Check Confluence API documentation: https://developer.atlassian.com/cloud/confluence/rest/
