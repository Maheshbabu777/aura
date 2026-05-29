"""
Configuration management using Pydantic and python-dotenv.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:1b"

    # Google Gemini Configuration
    gemini_api_key: str
    gemini_model: str = "gemini-3.5-flash"

    # Groq Configuration (Fast intent routing)
    groq_api_key: Optional[str] = None
    groq_model: str = "gemma2-9b-it"

    # Composio Configuration
    composio_api_key: Optional[str] = None

    # Database paths
    memory_db_path: str = "./data/chromadb"
    sqlite_db_path: str = "./data/memory.db"
    audit_log_path: str = "./data/audit.db"
    goal_db_path: str = "./data/goals.db"

    # Email Triage Configuration
    email_triage_model: str = "gemma3:1b"  # Lightweight model for email classification
    email_triage_use_cloud: bool = False  # Set True to use Gemini (privacy tradeoff)

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
