"""
Card Model
Schema for payment cards (encrypted sensitive data)
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId


class CardBase(BaseModel):
    """Base card fields"""
    card_holder: str = Field(..., min_length=2, max_length=100)
    card_type: str = Field(..., pattern="^(visa|mastercard|amex)$")
    last_four: str = Field(..., pattern="^[0-9]{4}$")
    expiry_month: int = Field(..., ge=1, le=12)
    expiry_year: int = Field(..., ge=2026, le=2050)
    is_default: bool = False


class CardCreate(CardBase):
    """Card creation schema (includes full number and CVV)"""
    card_number: str = Field(..., pattern="^[0-9]{13,19}$")
    cvv: str = Field(..., pattern="^[0-9]{3,4}$")
    user_id: str  # Owner of the card


class CardInDB(CardBase):
    """Card as stored in database (encrypted)"""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    user_id: str
    encrypted_number: str  # AES encrypted full card number
    cvv_hash: str  # SHA256 hash of CVV (not stored in plain text)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None
    is_active: bool = True
    
    class Config:
        populate_by_name = True


class Card(CardBase):
    """Card response schema (safe for API responses)"""
    id: str = Field(..., alias="_id")
    created_at: datetime
    last_used_at: Optional[datetime]
    is_active: bool
    
    class Config:
        populate_by_name = True
