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
    ENVIRONMENT: str = "development"
    
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
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1", "testserver"]
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:5500"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: list[str] = ["Authorization", "Content-Type", "X-Requested-With"]

    # Security hardening
    SECURITY_HEADERS_ENABLED: bool = True
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 120
    
    # Liveness Detection
    LIVENESS_TIMEOUT_SECONDS: int = 90
    LIVENESS_NO_FACE_TIMEOUT_SECONDS: int = 5
    LIVENESS_ENABLE_PASSIVE: bool = True
    
    # Risk Engine Thresholds
    RISK_HIGH_THRESHOLD: int = 60
    RISK_MEDIUM_THRESHOLD: int = 26
    LIVENESS_TRIGGER_THRESHOLD: int = 26  # Trigger liveness at risk > 25
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
