"""
Merchant Model
Schema for merchants/stores with geolocation
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from bson import ObjectId


class MerchantCategory(str, Enum):
    """Merchant business categories"""
    RESTAURANT = "restaurant"
    CAFE = "cafe"
    SUPERMARKET = "supermarket"
    PHARMACY = "pharmacy"
    CLOTHING = "clothing"
    ELECTRONICS = "electronics"
    FUEL_STATION = "fuel_station"
    HOTEL = "hotel"
    BAR = "bar"
    BAKERY = "bakery"
    OTHER = "other"


class MerchantLocation(BaseModel):
    """Merchant geographic location"""
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    address: str
    city: str
    postal_code: Optional[str] = None
    country: str = "Portugal"


class MerchantBase(BaseModel):
    """Base merchant fields"""
    name: str = Field(..., min_length=2, max_length=200)
    category: MerchantCategory
    location: MerchantLocation
    phone: Optional[str] = None
    email: Optional[str] = None


class MerchantCreate(MerchantBase):
    """Merchant creation schema"""
    pass


class MerchantInDB(MerchantBase):
    """Merchant as stored in database"""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Business info
    description: Optional[str] = None
    website: Optional[str] = None
    
    # Statistics
    total_transactions: int = 0
    total_revenue: float = 0.0
    average_transaction: float = 0.0
    fraud_incidents: int = 0
    
    # Status
    is_active: bool = True
    verified: bool = False
    
    # Operating hours (24h format "HH:MM")
    opening_time: Optional[str] = None
    closing_time: Optional[str] = None
    
    class Config:
        allow_population_by_field_name = True


class Merchant(MerchantBase):
    """Merchant response schema"""
    id: str = Field(..., alias="_id")
    description: Optional[str]
    total_transactions: int
    is_active: bool
    verified: bool
    
    class Config:
        allow_population_by_field_name = True


class MerchantSearchResult(Merchant):
    """Merchant with distance from user location"""
    distance_km: float = Field(..., description="Distance from user in kilometers")
