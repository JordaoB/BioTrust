"""
Transactions API Routes
Create and manage payment transactions with risk analysis
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
from backend.database import get_database
from backend.models.transaction import (
    Transaction, TransactionCreate, TransactionStatus, RiskLevel
)
from backend.models.user import Location
from bson import ObjectId
import sys
import os

# Import risk engine
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.core.risk_engine import RiskEngine

router = APIRouter()
risk_engine = RiskEngine()


def serialize_doc(doc):
    """Convert MongoDB ObjectId to string"""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def calculate_distance(loc1: dict, loc2: dict) -> float:
    """Calculate distance between two locations in km using Haversine formula"""
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371  # Earth radius in km
    
    lat1, lon1 = radians(loc1["lat"]), radians(loc1["lon"])
    lat2, lon2 = radians(loc2["lat"]), radians(loc2["lon"]) 
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


@router.post("/", response_model=Transaction, status_code=201)
async def create_transaction(
    transaction_data: TransactionCreate,
    db=Depends(get_database)
):
    """
    Create new transaction with risk analysis
    Determines if liveness verification is required
    """
    try:
        # Fetch user
        user = await db.users.find_one({"_id": ObjectId(transaction_data.user_id) if ObjectId.is_valid(transaction_data.user_id) else transaction_data.user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Fetch card
        card = await db.cards.find_one({"_id": ObjectId(transaction_data.card_id) if ObjectId.is_valid(transaction_data.card_id) else transaction_data.card_id})
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        
        if card["user_id"] != transaction_data.user_id:
            raise HTTPException(status_code=403, detail="Card does not belong to user")
        
        if not card["is_active"]:
            raise HTTPException(status_code=400, detail="Card is not active")
        
        # Fetch merchant if provided
        merchant = None
        merchant_info = None
        if transaction_data.merchant_id:
            merchant = await db.merchants.find_one({"_id": ObjectId(transaction_data.merchant_id) if ObjectId.is_valid(transaction_data.merchant_id) else transaction_data.merchant_id})
            if merchant:
                merchant_info = {
                    "merchant_id": str(merchant["_id"]),
                    "name": merchant["name"],
                    "category": merchant["category"],
                    "location": {
                        "lat": merchant["location"]["lat"],
                        "lon": merchant["location"]["lon"]
                    },
                    "city": merchant["location"]["city"]
                }
        
        # Calculate distances
        distance_from_home = calculate_distance(
            user["home_location"],
            transaction_data.user_location
        )
        
        distance_from_merchant = None
        if merchant_info:
            distance_from_merchant = calculate_distance(
                transaction_data.user_location,
                merchant_info["location"]
            )
        
        # Risk analysis using existing risk engine
        transaction_for_risk = {
            "amount": transaction_data.amount,
            "location": {
                "city": transaction_data.user_location.get("city", "Unknown"),
                "country": user["home_location"].get("country", "Unknown"),
                "lat": transaction_data.user_location["lat"],
                "lon": transaction_data.user_location["lon"]
            },
            "timestamp": datetime.utcnow(),
            "transaction_type": str(transaction_data.type),
            "user_profile": {
                "average_transaction": user.get("average_transaction", 0.0),
                "max_transaction": user.get("max_transaction", 0.0),
                "home_location": user["home_location"],
                "last_transaction_location": user.get("last_transaction_location", user["home_location"]),
                "account_age_days": user.get("account_age_days", 0),
                "transactions_today": user.get("transactions_today", 0)
            }
        }
        
        risk_analysis = risk_engine.analyze_transaction(transaction_for_risk)
        risk_score = risk_analysis['risk_score']
        risk_level = RiskLevel.LOW
        if risk_score > 70:
            risk_level = RiskLevel.HIGH
        elif risk_score > 40:
            risk_level = RiskLevel.MEDIUM
        
        liveness_required = risk_score > 40  # Require liveness for medium/high risk
        
        # Create transaction document
        transaction_dict = {
            "user_id": transaction_data.user_id,
            "card_id": transaction_data.card_id,
            "merchant_id": transaction_data.merchant_id,
            "merchant_info": merchant_info,
            "amount": transaction_data.amount,
            "currency": transaction_data.currency,
            "transaction_type": transaction_data.type,
            "user_location": transaction_data.user_location,
            "distance_from_home_km": round(distance_from_home, 2),
            "distance_from_merchant_km": round(distance_from_merchant, 2) if distance_from_merchant else None,
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "liveness_required": liveness_required,
            "liveness_performed": False,
            "liveness_result": None,
            "status": TransactionStatus.PENDING if liveness_required else TransactionStatus.APPROVED,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await db.transactions.insert_one(transaction_dict)
        
        # Update user stats
        await db.users.update_one(
            {"_id": ObjectId(transaction_data.user_id) if ObjectId.is_valid(transaction_data.user_id) else transaction_data.user_id},
            {
                "$inc": {"transactions_today": 1},
                "$set": {"last_transaction_location": transaction_data.user_location},
                "$push": {"location_history": transaction_data.user_location}
            }
        )
        
        # Update merchant stats if applicable
        if transaction_data.merchant_id:
            await db.merchants.update_one(
                {"_id": ObjectId(transaction_data.merchant_id) if ObjectId.is_valid(transaction_data.merchant_id) else transaction_data.merchant_id},
                {"$inc": {"total_transactions": 1}}
            )
        
        # Fetch created transaction
        created_transaction = await db.transactions.find_one({"_id": result.inserted_id})
        return serialize_doc(created_transaction)
        
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


@router.get("/{transaction_id}", response_model=Transaction)
async def get_transaction(transaction_id: str, db=Depends(get_database)):
    """Get transaction by ID"""
    transaction = await db.transactions.find_one({"_id": ObjectId(transaction_id) if ObjectId.is_valid(transaction_id) else transaction_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return serialize_doc(transaction)


@router.get("/user/{user_id}", response_model=List[Transaction])
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


@router.patch("/{transaction_id}/liveness")
async def update_transaction_liveness(
    transaction_id: str,
    liveness_result: dict,
    db=Depends(get_database)
):
    """
    Update transaction with liveness verification result
    Called after liveness verification is completed
    """
    
    transaction_obj_id = ObjectId(transaction_id) if ObjectId.is_valid(transaction_id) else transaction_id
    transaction = await db.transactions.find_one({"_id": transaction_obj_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if not transaction["liveness_required"]:
        raise HTTPException(status_code=400, detail="Liveness not required for this transaction")
    
    # Determine final status based on liveness result
    liveness_success = liveness_result.get("success", False)
    new_status = TransactionStatus.APPROVED if liveness_success else TransactionStatus.REJECTED
    
    # Update transaction
    await db.transactions.update_one(
        {"_id": transaction_obj_id},
        {
            "$set": {
                "liveness_performed": True,
                "liveness_result": liveness_result,
                "status": new_status,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    # Update user liveness count
    await db.users.update_one(
        {"_id": ObjectId(transaction["user_id"]) if ObjectId.is_valid(transaction["user_id"]) else transaction["user_id"]},
        {"$inc": {"liveness_verifications_count": 1}}
    )
    
    # Fetch updated transaction
    updated_transaction = await db.transactions.find_one({"_id": transaction_obj_id})
    return serialize_doc(updated_transaction)
