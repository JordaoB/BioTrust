"""
Users API Routes
Manage user accounts and profiles
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from backend.database import get_database
from backend.models.user import User, UserCreate
import hashlib
from bson import ObjectId


def serialize_doc(doc):
    """Convert MongoDB ObjectId to string"""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


router = APIRouter()


@router.get("/{user_id}", response_model=User)
async def get_user(user_id: str, db=Depends(get_database)):
    """Get user by ID"""
    user = await db.users.find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return serialize_doc(user)


@router.get("/email/{email}", response_model=User)
async def get_user_by_email(email: str, db=Depends(get_database)):
    """Get user by email"""
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return serialize_doc(user)


@router.get("/", response_model=List[User])
async def list_users(skip: int = 0, limit: int = 10, db=Depends(get_database)):
    """List all users (paginated)"""
    cursor = db.users.find().skip(skip).limit(limit)
    users = await cursor.to_list(length=limit)
    return [serialize_doc(user) for user in users]


@router.post("/", response_model=User, status_code=201)
async def create_user(user_data: UserCreate, db=Depends(get_database)):
    """Create new user"""
    from datetime import datetime
    
    # Check if email already exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password (simple SHA256 for demo)
    hashed_password = hashlib.sha256(user_data.password.encode()).hexdigest()
    
    # Create user document
    user_dict = user_data.dict(exclude={"password"})
    user_dict["hashed_password"] = hashed_password
    user_dict["created_at"] = datetime.utcnow()
    user_dict["account_age_days"] = 0
    user_dict["average_transaction"] = 0.0
    user_dict["max_transaction"] = 0.0
    user_dict["transactions_today"] = 0
    user_dict["failed_transactions_last_week"] = 0
    user_dict["location_history"] = []
    user_dict["last_transaction_location"] = None
    user_dict["card_ids"] = []
    user_dict["is_verified"] = False
    user_dict["liveness_verifications_count"] = 0
    
    result = await db.users.insert_one(user_dict)
    
    # Fetch and return created user
    created_user = await db.users.find_one({"_id": result.inserted_id})
    return serialize_doc(created_user)


@router.get("/{user_id}/cards")
async def get_user_cards(user_id: str, db=Depends(get_database)):
    """Get all cards for a user"""
    cards = await db.cards.find({"user_id": user_id}).to_list(length=100)
    if not cards:
        return []
    
    # Return safe card info (no sensitive data)
    return [
        {
            "id": str(card["_id"]),
            "card_type": card["card_type"],
            "last_four": card["last_four"],
            "expiry_month": card["expiry_month"],
            "expiry_year": card["expiry_year"],
            "is_default": card["is_default"],
            "is_active": card["is_active"]
        }
        for card in cards
    ]


@router.get("/{user_id}/transactions")
async def get_user_transactions(
    user_id: str,
    skip: int = 0,
    limit: int = 20,
    db=Depends(get_database)
):
    """Get transaction history for a user"""
    cursor = db.transactions.find(
        {"user_id": user_id}
    ).sort("created_at", -1).skip(skip).limit(limit)
    
    transactions = await cursor.to_list(length=limit)
    return [serialize_doc(tx) for tx in transactions]
