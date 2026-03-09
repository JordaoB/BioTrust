"""
Session Model
Persistent session storage in MongoDB with access and refresh tokens
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class Session(BaseModel):
    """
    Session document for MongoDB
    Stores access and refresh tokens with expiration
    """
    user_id: str = Field(..., description="User ID (ObjectId as string)")
    email: str = Field(..., description="User email")
    access_token: str = Field(..., description="Short-lived access token (1 hour)")
    refresh_token: str = Field(..., description="Long-lived refresh token (30 days)")
    access_token_expires_at: datetime = Field(..., description="Access token expiration")
    refresh_token_expires_at: datetime = Field(..., description="Refresh token expiration")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    is_active: bool = Field(default=True, description="Session active status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                "access_token_expires_at": "2026-03-09T15:00:00",
                "refresh_token_expires_at": "2026-04-08T14:00:00",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0...",
                "is_active": True
            }
        }


class TokenPair(BaseModel):
    """Response model for token operations"""
    access_token: str
    refresh_token: str
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
    token_type: str = "Bearer"


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh"""
    refresh_token: str = Field(..., description="Valid refresh token")
