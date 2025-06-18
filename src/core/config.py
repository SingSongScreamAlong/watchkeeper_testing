"""
Configuration settings for WATCHKEEPER Testing Edition.

This module provides configuration settings loaded from environment variables.
"""

import os
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Optimized for lightweight operation on a 2014 Mac Mini.
    """
    # Project info
    PROJECT_NAME: str = "WATCHKEEPER Testing Edition"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "Lightweight intelligence platform for missionary operations"
    
    # Database
    DATABASE_URL: str = "sqlite:///./data/threats.db"
    
    # API settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    
    # Ollama AI
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    AI_MODEL: str = "llama3.2:3b"
    AI_TIMEOUT: int = 300  # seconds
    
    # Collection settings
    COLLECTION_FREQUENCY: int = 30  # minutes
    MAX_ARTICLES_PER_SOURCE: int = 10
    PROCESSING_DELAY: int = 2  # seconds between AI requests
    
    # Testing settings
    TESTING_MODE: bool = True
    ALPHA_USERS_MAX: int = 5
    FEEDBACK_COLLECTION: bool = True
    
    # CORS settings for SENTINEL integration
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]
    
    @validator("DATABASE_URL")
    def validate_database_url(cls, v: str) -> str:
        """Ensure database directory exists"""
        if v.startswith("sqlite:///"):
            db_path = v.replace("sqlite:///", "")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()
