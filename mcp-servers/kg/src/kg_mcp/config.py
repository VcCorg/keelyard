"""Configuration for KG MCP Server."""

from pydantic_settings import BaseSettings


class KGConfig(BaseSettings):
    """Knowledge Graph MCP Server configuration."""

    # Neo4j connection
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    # LightRAG connection
    lightrag_url: str = "http://localhost:8001"
    lightrag_timeout: float = 120.0

    # Default provider
    default_provider: str = "lightrag"

    # DVA CLI config file path (source of truth for data sources)
    # In Docker: mount ~/.dva-agentic/ as volume
    source_registry_path: str = "~/.dva-agentic/config.json"

    model_config = {
        "env_prefix": "KG_",
        "env_file": ".env",
        "extra": "ignore",
    }

    @property
    def is_neo4j_configured(self) -> bool:
        """Check if Neo4j connection is configured."""
        return bool(self.neo4j_uri and self.neo4j_password)

    @property
    def is_lightrag_configured(self) -> bool:
        """Check if LightRAG is configured."""
        return bool(self.lightrag_url)
