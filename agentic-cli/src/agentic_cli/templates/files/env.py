"""Generate .env.example content."""

from agentic_cli.templates.config import TemplateConfig
from agentic_cli.templates.enums import Tool, UseCase


def get_env_content(config: TemplateConfig) -> str:
    """Generate .env.example content based on configuration."""
    content = '''# Agent Configuration
AGENT_PROVIDER=vertex_ai

# Google Cloud Configuration
GOOGLE_PROJECT_ID=your-project-id
GOOGLE_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Vertex AI Model
VERTEX_AI_MODEL=gemini-2.0-flash-001
'''
    
    if Tool.KG_QUERY in config.tools or Tool.KG_INGEST in config.tools:
        content += '''
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
'''
    
    if Tool.VECTOR_SEARCH in config.tools:
        content += '''
# Vector Database
CHROMA_PERSIST_DIR=./chroma_db
'''
    
    if Tool.DATABASE_TOOL in config.tools:
        content += '''
# Database
DATABASE_URL=sqlite:///./data.db
'''
    
    if Tool.WEB_SEARCH in config.tools:
        content += '''
# Web Search (optional)
SERPER_API_KEY=your-serper-api-key
'''
    
    if Tool.MEMORY in config.tools and config.use_case != UseCase.PR_REVIEWER:
        content += '''
# Memory Configuration
MEMORY_PERSISTENT=false
MEMORY_DB_PATH=./data/memory.db
MEMORY_SESSION_ID=default
'''
    
    if config.use_case == UseCase.PR_REVIEWER:
        content += f'''
# Bitbucket MCP (required)
BITBUCKET_MCP_URL={config.bitbucket_mcp_url}

# PR Watcher Settings
POLL_INTERVAL={config.poll_interval}
REVIEW_MODE=review  # notify, review, auto-approve
STATE_FILE=./data/pr_state.json

# Auto-approve rules
MAX_FILES_FOR_AUTO_APPROVE=10
MAX_DIFF_LINES_FOR_AUTO_APPROVE=500
'''
        if config.include_jira_mcp:
            content += f'''
# Jira MCP (optional)
JIRA_MCP_URL={config.jira_mcp_url}
'''
    
    return content
