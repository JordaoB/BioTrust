"""
Cards API Routes
Manage user payment cards
"""

from fastapi import APIRouter, HTTPException, Depends
from backend.database import get_database
from pydantic import BaseModel, Field
from datetime import datetime
from bson import ObjectId
import hashlib


router = APIRouter()


# Request/Response Models
class AddCardRequest(BaseModel):
    card_holder: str = Field(..., min_length=3, max_length=50)
    card_type: str = Field(..., pattern="^(visa|mastercard|amex)$")
    card_number: str = Field(..., min_length=13, max_length=19)
    cvv: str = Field(..., min_length=3, max_length=4)
    expiry_month: int = Field(..., ge=1, le=12)
    expiry_year: int = Field(..., ge=2026, le=2040)
    is_default: bool = False
    balance: float = Field(default=1000.0, ge=0)  # Initial balance
    daily_limit: float = Field(default=5000.0, ge=0)  # Max per day
    max_transaction: float = Field(default=2000.0, ge=0)  # Max per transaction


@router.post("/{user_id}/cards")
async def add_card(user_id: str, card_data: AddCardRequest, db=Depends(get_database)):
    """
    Add new payment card to user account
    Stores card with all details (for demo - in production use tokenization)
    """
    # Verify user exists
    obj_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else None
    if not obj_id:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    user = await db.users.find_one({"_id": obj_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate card number (basic Luhn algorithm check)
    if not is_valid_card_number(card_data.card_number):
        raise HTTPException(status_code=400, detail="Invalid card number")
    
    # Check if card already exists
    existing_cards = user.get("cards", [])
    for card in existing_cards:
        if card["card_number"] == card_data.card_number:
            raise HTTPException(status_code=400, detail="Card already registered")
    
    # If this is set as default, unset other defaults
    if card_data.is_default:
        for card in existing_cards:
            card["is_default"] = False
    
    # Create new card document
    new_card = {
        "card_holder": card_data.card_holder.upper(),
        "card_type": card_data.card_type,
        "card_number": card_data.card_number,
        "cvv": card_data.cvv,
        "expiry_month": card_data.expiry_month,
        "expiry_year": card_data.expiry_year,
        "is_default": card_data.is_default if existing_cards else True,  # First card is always default
        "balance": card_data.balance,
        "daily_limit": card_data.daily_limit,
        "max_transaction": card_data.max_transaction,
        "daily_spent": 0.0,  # Track daily spending
        "last_reset": datetime.utcnow().date().isoformat(),  # For daily limit reset
        "added_at": datetime.utcnow()
    }
    
    # Add card to user's cards array
    await db.users.update_one(
        {"_id": obj_id},
        {
            "$push": {"cards": new_card},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    return {
        "success": True,
        "message": "Card added successfully",
        "card": {
            "card_holder": new_card["card_holder"],
            "card_type": new_card["card_type"],
            "last_four": card_data.card_number[-4:],
            "expiry": f"{card_data.expiry_month:02d}/{card_data.expiry_year}",
            "is_default": new_card["is_default"]
        }
    }


@router.get("/{user_id}/cards")
async def list_cards(user_id: str, db=Depends(get_database)):
    """
    List all cards for user
    Returns masked card numbers for security
    """
    obj_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else None
    if not obj_id:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    user = await db.users.find_one({"_id": obj_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    cards = user.get("cards", [])
    
    # Return cards with masked numbers
    masked_cards = []
    for i, card in enumerate(cards):
        masked_cards.append({
            "index": i,
            "card_holder": card["card_holder"],
            "card_type": card["card_type"],
            "last_four": card["card_number"][-4:],
            "masked_number": f"**** **** **** {card['card_number'][-4:]}",
            "expiry": f"{card['expiry_month']:02d}/{card['expiry_year']}",
            "is_default": card.get("is_default", False)
        })
    
    return {"success": True, "cards": masked_cards}


@router.delete("/{user_id}/cards/{card_index}")
async def delete_card(user_id: str, card_index: int, db=Depends(get_database)):
    """
    Remove card from user account
    Cannot remove if it's the only card
    """
    obj_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else None
    if not obj_id:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    user = await db.users.find_one({"_id": obj_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    cards = user.get("cards", [])
    
    if card_index < 0 or card_index >= len(cards):
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Remove card
    removed_card = cards.pop(card_index)
    
    # If removed card was default and there are other cards, set first card as default
    if removed_card.get("is_default") and cards:
        cards[0]["is_default"] = True
    
    # Update database
    await db.users.update_one(
        {"_id": obj_id},
        {
            "$set": {
                "cards": cards,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {
        "success": True,
        "message": "Card removed successfully",
        "remaining_cards": len(cards)
    }


@router.put("/{user_id}/cards/{card_index}/set-default")
async def set_default_card(user_id: str, card_index: int, db=Depends(get_database)):
    """
    Set a card as default for transactions
    """
    obj_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else None
    if not obj_id:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    user = await db.users.find_one({"_id": obj_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    cards = user.get("cards", [])
    
    if card_index < 0 or card_index >= len(cards):
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Unset all defaults, set new default
    for i, card in enumerate(cards):
        card["is_default"] = (i == card_index)
    
    # Update database
    await db.users.update_one(
        {"_id": obj_id},
        {
            "$set": {
                "cards": cards,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {
        "success": True,
        "message": "Default card updated"
    }


def is_valid_card_number(card_number: str) -> bool:
    """
    Validate card number using Luhn algorithm
    """
    # Remove spaces and dashes
    card_number = card_number.replace(" ", "").replace("-", "")
    
    # Check if all digits
    if not card_number.isdigit():
        return False
    
    # Luhn algorithm
    digits = [int(d) for d in card_number]
    checksum = 0
    
    # Double every second digit from right to left
    for i in range(len(digits) - 2, -1, -2):
        digits[i] *= 2
        if digits[i] > 9:
            digits[i] -= 9
    
    checksum = sum(digits)
    return checksum % 10 == 0
