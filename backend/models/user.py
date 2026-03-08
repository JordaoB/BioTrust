"""
User Model
Schema for user accounts with geolocation history
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic v2"""
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema
        return core_schema.union_schema([
            core_schema.is_instance_schema(ObjectId),
            core_schema.no_info_plain_validator_function(
                cls.validate,
                serialization=core_schema.plain_serializer_function_ser_schema(
                    lambda x: str(x)
                )
            )
        ])

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str) and ObjectId.is_valid(v):
            return ObjectId(v)
        raise ValueError("Invalid ObjectId")


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
        populate_by_name = True
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
        populate_by_name = True
