"""
Users API Routes
Manage user accounts and profiles
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
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
    try:
        # Convert string to ObjectId if valid
        user_id_obj = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        user = await db.users.find_one({"_id": user_id_obj})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid user ID format: {str(e)}")
    
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
    # Convert string to ObjectId if valid
    user_id_obj = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
    
    # Primeiro tenta buscar da coleção separada de cartões
    cards = await db.cards.find({"user_id": user_id}).to_list(length=100)
    
    # Se não encontrar, busca os cartões inline do documento do utilizador
    if not cards:
        user = await db.users.find_one({"_id": user_id_obj})
        if user and "cards" in user:
            # Converte cartões inline para o formato esperado
            inline_cards = user["cards"]
            today = datetime.utcnow().date().isoformat()
            return {
                "success": True,
                "cards": [
                    {
                        "_id": f"{user_id}_card_{i}",  # ID fictício
                        "card_type": card["card_type"],
                        "card_number": card["card_number"],  # Full number for frontend
                        "masked_number": f"**** **** **** {card['card_number'][-4:]}",
                        "last_four": card["card_number"][-4:],
                        "card_holder": card.get("card_holder", "N/A"),
                        "expiry_month": card["expiry_month"],
                        "expiry_year": card["expiry_year"],
                        "expiry": f"{card['expiry_month']:02d}/{str(card['expiry_year'])[-2:]}",
                        "is_default": card.get("is_default", False),
                        "is_active": True,
                        "balance": card.get("balance", 0.0),
                        "daily_limit": card.get("daily_limit", 5000.0),
                        "max_transaction": card.get("max_transaction", 2000.0),
                        "daily_spent": card.get("daily_spent", 0.0) if card.get("last_reset") == today else 0.0
                    }
                    for i, card in enumerate(inline_cards)
                ]
            }
        return {"success": True, "cards": []}
    
    # Retorna cartões da coleção separada (formato seguro)
    return {
        "success": True,
        "cards": [
            {
                "_id": str(card["_id"]),
                "card_type": card["card_type"],
                "masked_number": f"**** **** **** {card['last_four']}",
                "last_four": card["last_four"],
                "card_holder": card.get("card_holder", "N/A"),
                "expiry_month": card["expiry_month"],
                "expiry_year": card["expiry_year"],
                "expiry": f"{card['expiry_month']:02d}/{str(card['expiry_year'])[-2:]}",
                "is_default": card["is_default"],
                "is_active": card["is_active"]
            }
            for card in cards
        ]
    }


@router.get("/{user_id}/transactions")
async def get_user_transactions(
    user_id: str,
    skip: int = 0,
    limit: int = 20,
    db=Depends(get_database)
):
    """Get transaction history for a user"""
    # No need to convert user_id to ObjectId here because transactions store it as string
    cursor = db.transactions.find(
        {"user_id": user_id}
    ).sort("created_at", -1).skip(skip).limit(limit)
    
    transactions = await cursor.to_list(length=limit)
    return [serialize_doc(tx) for tx in transactions]


@router.get("/{user_id}/contacts")
async def get_contacts(user_id: str, db=Depends(get_database)):
    """
    Get all registered users as contacts (except current user)
    Returns minimal info for contact selection: name, email, phone
    """
    # Convert string to ObjectId if valid
    user_id_obj = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
    
    # Get all users except current user
    cursor = db.users.find({"_id": {"$ne": user_id_obj}})
    users = await cursor.to_list(length=1000)
    
    # Return minimal contact info
    contacts = []
    for user in users:
        contacts.append({
            "_id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "phone": user.get("phone", ""),
            "initials": "".join([n[0].upper() for n in user["name"].split()[:2]])  # Ex: "João Silva" -> "JS"
        })
    
    return {"success": True, "contacts": contacts}
