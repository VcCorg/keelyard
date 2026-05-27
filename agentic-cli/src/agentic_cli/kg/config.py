"""Configuration management for knowledge graph."""

import json
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class KGConfig(BaseModel):
    """Knowledge graph configuration."""
    
    provider: str = Field(default="neo4j", description="Graph database provider (neo4j, lightrag, postgres, weaviate)")
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    neo4j_username: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: Optional[str] = Field(default=None, description="Neo4j password")
    embeddings_provider: str = Field(default="vertex-ai", description="Embeddings provider")
    
    # PostgreSQL settings (pgvector + Apache AGE)
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_user: str = Field(default="postgres", description="PostgreSQL username")
    postgres_password: str = Field(default="postgres", description="PostgreSQL password")
    postgres_database: str = Field(default="knowledge_graph", description="PostgreSQL database name")
    postgres_graph: str = Field(default="knowledge_graph", description="Apache AGE graph name")
    
    # LightRAG settings
    lightrag_url: str = Field(default="http://localhost:8001", description="LightRAG API base URL")
    lightrag_timeout: float = Field(default=300.0, description="LightRAG request timeout in seconds")
    
    # Weaviate settings
    weaviate_host: str = Field(default="localhost", description="Weaviate host")
    weaviate_port: int = Field(default=8080, description="Weaviate port")
    weaviate_scheme: str = Field(default="http", description="Weaviate connection scheme (http or https)")
    weaviate_api_key: Optional[str] = Field(default=None, description="Weaviate API key for authentication")
    
    # Workspace settings (LightRAG only)
    workspace: str = Field(default="default", description="Active workspace name (LightRAG only)")
    workspace_base_dir: str = Field(
        default_factory=lambda: os.path.expanduser("~/.agent-cli-agentic/lightrag-workspaces"),
        description="Base directory for workspaces (LightRAG only)"
    )
    
    # Vertex AI settings (loaded from main config if available)
    google_project_id: Optional[str] = Field(default=None, description="Google Cloud project ID")
    google_location: str = Field(default="us-central1", description="Google Cloud location")
    vertex_ai_model: str = Field(default="text-embedding-004", description="Vertex AI embedding model")
    
    # Confluence settings
    confluence_url: Optional[str] = Field(default=None, description="Confluence base URL (e.g., https://confluence.company.com)")
    confluence_username: Optional[str] = Field(default=None, description="Confluence username/email")
    confluence_api_token: Optional[str] = Field(default=None, description="Confluence API token or password")
    confluence_cloud: bool = Field(default=False, description="Whether Confluence is Cloud (True) or Server (False)")
    
    @classmethod
    def get_config_path(cls) -> Path:
        """Get the configuration file path."""
        config_dir = Path.home() / ".dva-agentic"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "kg-config.json"
    
    @classmethod
    def load(cls) -> "KGConfig":
        """Load configuration from file."""
        config_path = cls.get_config_path()
        
        # Load KG config if it exists
        kg_data = {}
        if config_path.exists():
            with open(config_path, "r") as f:
                kg_data = json.load(f)
        
        # Try to load Vertex AI settings from main config and merge
        main_config_path = Path.home() / ".agent-cli-agentic" / "config.json"
        if main_config_path.exists():
            with open(main_config_path, "r") as f:
                main_data = json.load(f)
                # Try both 'google' and 'vertex_ai' keys for compatibility
                vertex_config = main_data.get("google", main_data.get("vertex_ai", {}))
                
                # Merge Vertex AI settings if not already set in KG config
                if not kg_data.get("google_project_id") and vertex_config.get("project_id"):
                    kg_data["google_project_id"] = vertex_config.get("project_id")
                if not kg_data.get("google_location"):
                    kg_data["google_location"] = vertex_config.get("location", "us-central1")
                if not kg_data.get("vertex_ai_model"):
                    kg_data["vertex_ai_model"] = vertex_config.get("model", "gemini-pro")
        
        return cls(**kg_data) if kg_data else cls()
    
    def save(self) -> None:
        """Save configuration to file."""
        config_path = self.get_config_path()
        
        with open(config_path, "w") as f:
            json.dump(self.model_dump(), f, indent=2)
    
    def is_neo4j_configured(self) -> bool:
        """Check if Neo4j is properly configured."""
        return (
            self.provider == "neo4j"
            and self.neo4j_uri is not None
            and self.neo4j_username is not None
            and self.neo4j_password is not None
        )
    
    def is_vertex_ai_configured(self) -> bool:
        """Check if Vertex AI is properly configured."""
        return (
            self.embeddings_provider == "vertex-ai"
            and self.google_project_id is not None
        )
    
    def is_confluence_configured(self) -> bool:
        """Check if Confluence is properly configured."""
        return (
            self.confluence_url is not None
            and self.confluence_username is not None
            and self.confluence_api_token is not None
        )
    
    def is_lightrag_configured(self) -> bool:
        """Check if LightRAG is properly configured."""
        return (
            self.provider == "lightrag"
            and self.lightrag_url is not None
        )
    
    def is_postgres_configured(self) -> bool:
        """Check if PostgreSQL is properly configured."""
        return (
            self.provider == "postgres"
            and self.postgres_host is not None
            and self.postgres_user is not None
            and self.postgres_password is not None
        )
    
    def is_weaviate_configured(self) -> bool:
        """Check if Weaviate is properly configured."""
        return (
            self.provider == "weaviate"
            and self.weaviate_host is not None
        )
    
    def get_workspace_dir(self) -> str:
        """
        Get the full path to the current workspace directory.
        
        Only applicable for LightRAG provider. Returns workspace_base_dir for Neo4j.
        
        Returns:
            Full path to workspace directory
        """
        if self.provider == "lightrag":
            return f"{self.workspace_base_dir}/{self.workspace}"
        else:
            # For Neo4j, return base dir (workspaces not supported)
            return self.workspace_base_dir
    
    def supports_workspaces(self) -> bool:
        """
        Check if the current provider supports workspaces.
        
        Returns:
            True if provider supports workspaces (currently only LightRAG)
        """
        return self.provider == "lightrag"
