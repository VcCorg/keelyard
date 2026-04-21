"""Configuration management using Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Keys
    openai_api_key: str = Field(default="", description="OpenAI API key")
    anthropic_api_key: str = Field(default="", description="Anthropic API key")

    # Google Vertex AI Configuration
    google_project_id: str = Field(default="", description="Google Cloud Project ID")
    google_location: str = Field(default="us-central1", description="Google Cloud region/location")
    google_application_credentials: str = Field(
        default="", description="Path to Google service account JSON key file"
    )
    vertex_ai_model: str = Field(
        default="gemini-pro", description="Vertex AI model to use (e.g., gemini-pro, gemini-pro-vision)"
    )

    # Agent Configuration
    agent_model: str = Field(default="gpt-4", description="Default model to use")
    agent_temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature")
    agent_max_tokens: int = Field(default=2000, gt=0, description="Max tokens")
    agent_provider: Literal["openai", "anthropic", "vertex_ai"] = Field(
        default="openai", description="AI provider to use"
    )

    # Environment
    environment: Literal["development", "staging", "production"] = Field(
        default="development", description="Environment"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )

    # Optional: Custom endpoints
    openai_api_base: str = Field(default="https://api.openai.com/v1")
    anthropic_api_base: str = Field(default="https://api.anthropic.com")

    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"

    def is_vertex_ai_configured(self) -> bool:
        """Check if Vertex AI is properly configured."""
        return bool(self.google_project_id and self.google_location)

    def get_vertex_ai_config(self) -> dict:
        """Get Vertex AI configuration as a dictionary."""
        return {
            "project_id": self.google_project_id,
            "location": self.google_location,
            "credentials_path": self.google_application_credentials,
            "model": self.vertex_ai_model,
        }


# Global settings instance
settings = Settings()
