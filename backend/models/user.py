"""
User Model
Schema for user accounts with geolocation history
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic"""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class Location(BaseModel):
    """User location (home or last transaction)"""
    city: str
    country: str = "Portugal"
    lat: float
    lon: float


class UserBase(BaseModel):
    """Base user fields"""
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    home_location: Location
    

class UserCreate(UserBase):
    """User creation schema (includes password)"""
    password: str = Field(..., min_length=6)


class UserInDB(UserBase):
    """User as stored in database"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    account_age_days: int = 0
    
    # Transaction statistics
    average_transaction: float = 0.0
    max_transaction: float = 0.0
    transactions_today: int = 0
    failed_transactions_last_week: int = 0
    
    # Location history (last 10 transactions)
    location_history: List[Location] = []
    last_transaction_location: Optional[Location] = None
    last_transaction_at: Optional[datetime] = None
    
    # Cards
    card_ids: List[str] = []  # References to Card collection
    
    # Verification status
    is_verified: bool = False
    liveness_verifications_count: int = 0
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class User(UserBase):
    """User response schema (excludes sensitive data)"""
    id: str = Field(..., alias="_id")
    created_at: datetime
    account_age_days: int
    average_transaction: float
    transactions_today: int
    is_verified: bool
    liveness_verifications_count: int
    
    class Config:
        allow_population_by_field_name = True
