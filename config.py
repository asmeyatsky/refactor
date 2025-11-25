"""
Configuration module for Cloud Refactor Agent
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Centralized configuration for the application"""
    
    # API Server Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_RELOAD: bool = os.getenv("API_RELOAD", "true").lower() == "true"
    
    # Storage Paths
    CODEBASE_STORAGE_PATH: str = os.getenv("CODEBASE_STORAGE_PATH", "/tmp/codebases")
    PLAN_STORAGE_PATH: str = os.getenv("PLAN_STORAGE_PATH", "/tmp/plans")
    BACKUP_STORAGE_PATH: str = os.getenv("BACKUP_STORAGE_PATH", "/tmp/refactor_backups")
    MEMORY_STORAGE_PATH: str = os.getenv("MEMORY_STORAGE_PATH", "/tmp/memory_module")
    
    # LLM Provider Configuration - Gemini only
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    
    # Google Cloud Configuration
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "refactord-479213")
    GCP_REGION: str = os.getenv("GCP_REGION", "asia-south1")  # Mumbai
    
    # Test Runner Configuration
    TEST_RUNNER: str = os.getenv("TEST_RUNNER", "pytest")  # pytest, unittest, mock
    TEST_TIMEOUT: int = int(os.getenv("TEST_TIMEOUT", "300"))
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE")
    
    # Frontend Configuration
    REACT_APP_API_BASE_URL: str = os.getenv("REACT_APP_API_BASE_URL", "http://localhost:8000")
    
    # Security Configuration
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all storage directories exist"""
        Path(cls.CODEBASE_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
        Path(cls.PLAN_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
        Path(cls.BACKUP_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
        Path(cls.MEMORY_STORAGE_PATH).mkdir(parents=True, exist_ok=True)


# Create a global config instance
config = Config()
