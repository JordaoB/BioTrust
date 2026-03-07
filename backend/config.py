"""
Configuration
Environment variables and app settings
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # App
    APP_NAME: str = "BioTrust"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True
    
    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "biotrust"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Encryption (for card numbers)
    ENCRYPTION_KEY: str = "your-32-byte-encryption-key-here"
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:5500"]
    
    # Liveness Detection
    LIVENESS_TIMEOUT_SECONDS: int = 90
    LIVENESS_ENABLE_PASSIVE: bool = True
    
    # Risk Engine Thresholds
    RISK_HIGH_THRESHOLD: int = 60
    RISK_MEDIUM_THRESHOLD: int = 35
    LIVENESS_TRIGGER_THRESHOLD: int = 50  # Trigger liveness at risk >= 50
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
