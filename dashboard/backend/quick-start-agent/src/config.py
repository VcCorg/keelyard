"""Application configuration using Pydantic Settings."""

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

    # Memory Configuration
    memory_persistent: bool = False
    memory_db_path: str = "./data/memory.db"
    memory_session_id: str = "default"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
