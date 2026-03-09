"""
Transaction Model
Schema for payment transactions with risk analysis and liveness verification
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from bson import ObjectId


class TransactionType(str, Enum):
    """Transaction types"""
    PHYSICAL = "physical"  # In-person purchase
    ONLINE = "online"  # Online purchase
    ATM = "atm"  # ATM withdrawal
    TRANSFER = "transfer"  # Bank transfer


class TransactionStatus(str, Enum):
    """Transaction status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_VERIFICATION = "requires_verification"


class RiskLevel(str, Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MerchantInfo(BaseModel):
    """Merchant information within transaction"""
    merchant_id: Optional[str] = None
    name: str
    category: str  # restaurant, pharmacy, supermarket, etc
    location: Dict[str, Any]  # {"lat": 38.7223, "lon": -9.1393, "city": "Lisboa"}
    city: str


class LivenessResult(BaseModel):
    """Liveness verification result"""
    success: bool
    challenges_completed: int  # Número de desafios completados (0-5)
    heart_rate: Optional[float] = None
    heart_rate_confidence: Optional[float] = None
    anti_spoofing: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TransactionBase(BaseModel):
    """Base transaction fields"""
    amount: float = Field(..., gt=0)
    currency: str = "EUR"
    type: TransactionType
    description: Optional[str] = None


class TransactionCreate(TransactionBase):
    """Transaction creation schema"""
    user_id: str
    card_id: Optional[str] = None  # Optional - deprecated, use card_index
    card_index: Optional[int] = None  # Index of card in user's cards array
    merchant_id: Optional[str] = None
    recipient_email: Optional[str] = None  # For transfers
    user_location: Dict[str, Any]  # Current user location {"lat": x, "lon": y, "city": "Lisboa"}


class TransactionInDB(TransactionBase):
    """Transaction as stored in database"""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    user_id: str
    card_id: Optional[str] = None  # Optional - using card_index now
    card_index: Optional[int] = None  # Index in user's cards array
    merchant: MerchantInfo
    
    # User location at transaction time
    user_location: Dict[str, Any]  # {"lat", "lon", "city"}
    distance_from_home_km: Optional[float] = None
    distance_from_merchant_km: Optional[float] = None
    
    # Risk analysis
    risk_score: int  # 0-100
    risk_level: RiskLevel
    risk_factors: Dict[str, Any] = {}  # Detailed risk breakdown
    
    # Status
    status: TransactionStatus
    
    # Liveness verification (if performed)
    liveness_required: bool = False
    liveness_performed: bool = False
    liveness_result: Optional[LivenessResult] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    
    # Approval
    approved: bool = False
    rejection_reason: Optional[str] = None
    
    class Config:
        populate_by_name = True


class Transaction(TransactionBase):
    """Transaction response schema"""
    id: str = Field(..., alias="_id")
    user_id: str
    card_id: Optional[str] = None  # Optional - using card_index now
    card_index: Optional[int] = None  # Index in user's cards array
    merchant_id: Optional[str] = None
    merchant_info: Optional[MerchantInfo] = None
    user_location: Dict[str, Any]  # {"lat", "lon", "city"}
    distance_from_home_km: float
    distance_from_merchant_km: Optional[float] = None
    risk_score: float
    risk_level: RiskLevel
    status: TransactionStatus
    liveness_required: bool
    liveness_performed: bool
    liveness_result: Optional[LivenessResult] = None
    created_at: datetime
    updated_at: datetime
    
    # Override type field to accept transaction_type from DB
    type: TransactionType = Field(..., alias="transaction_type")
    
    class Config:
        populate_by_name = True
