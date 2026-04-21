"""Generate config.py content."""

from dva_agentic_cli.templates.config import TemplateConfig
from dva_agentic_cli.templates.enums import Tool, UseCase


def get_config_content(config: TemplateConfig) -> str:
    """Generate config.py content based on configuration."""
    extra_settings = ""
    
    if Tool.KG_QUERY in config.tools or Tool.KG_INGEST in config.tools:
        extra_settings += '''
    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "password"
'''
    
    if Tool.VECTOR_SEARCH in config.tools:
        extra_settings += '''
    # Vector Database
    chroma_persist_dir: str = "./chroma_db"
'''
    
    if Tool.DATABASE_TOOL in config.tools:
        extra_settings += '''
    # Database
    database_url: str = "sqlite:///./data.db"
'''
    
    if Tool.MEMORY in config.tools and config.use_case != UseCase.PR_REVIEWER:
        extra_settings += '''
    # Memory Configuration
    memory_persistent: bool = False
    memory_db_path: str = "./data/memory.db"
    memory_session_id: str = "default"
'''
    
    if config.use_case == UseCase.PR_REVIEWER:
        extra_settings += f'''
    # Bitbucket MCP (required)
    bitbucket_mcp_url: str = "{config.bitbucket_mcp_url}"
    
    # PR Watcher Settings
    poll_interval: int = {config.poll_interval}
    review_mode: str = "review"  # notify, review, auto-approve
    state_file: str = "./data/pr_state.json"
    
    # Auto-approve rules
    max_files_for_auto_approve: int = 10
    max_diff_lines_for_auto_approve: int = 500
'''
        if config.include_jira_mcp:
            extra_settings += f'''
    # Jira MCP (optional)
    jira_mcp_url: str = "{config.jira_mcp_url}"
'''
    
    return f'''"""Application configuration using Pydantic Settings."""

from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Agent provider
    agent_provider: str = "vertex_ai"
    
    # Google Cloud
    google_project_id: Optional[str] = None
    google_location: str = "us-central1"
    google_application_credentials: Optional[str] = None
    
    # Vertex AI
    vertex_ai_model: str = "gemini-2.0-flash-001"
{extra_settings}
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
'''
