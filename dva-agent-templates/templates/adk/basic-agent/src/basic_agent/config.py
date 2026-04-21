"""Configuration management for Basic Agent."""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Google Cloud Configuration
    google_project_id: str = Field(..., env="GOOGLE_PROJECT_ID")
    google_location: str = Field(default="us-central1", env="GOOGLE_LOCATION")
    google_application_credentials: Optional[str] = Field(None, env="GOOGLE_APPLICATION_CREDENTIALS")
    vertex_ai_model: str = Field(default="gemini-2.0-flash-001", env="VERTEX_AI_MODEL")
    
    # Agent Configuration
    agent_name: str = Field(default="basic-agent", env="AGENT_NAME")
    agent_description: str = Field(default="A basic agent using Google ADK framework", env="AGENT_DESCRIPTION")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @property
    def is_configured(self) -> bool:
        """Check if essential configuration is present."""
        return bool(self.google_project_id)
    
    def get_credentials_path(self) -> Optional[Path]:
        """Get the path to Google Cloud credentials."""
        if self.google_application_credentials:
            return Path(self.google_application_credentials)
        return None


# Global settings instance
settings = Settings()
