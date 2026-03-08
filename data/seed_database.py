"""
Database Seeding Script
Populates MongoDB with initial merchants and users
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from cryptography.fernet import Fernet
import hashlib
import base64

# Simple password hashing for demo (use proper bcrypt in production)
def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

# Card encryption (use a fixed key for demo, generate proper one for production)
# Fernet requires exactly 32 bytes, base64url-encoded (results in 44 chars)
key_bytes = b'0123456789abcdefghijklmnopqrstuv'  # Exactly 32 ASCII bytes
DEMO_ENCRYPTION_KEY = base64.urlsafe_b64encode(key_bytes)
cipher = Fernet(DEMO_ENCRYPTION_KEY)


def encrypt_card_number(card_number: str) -> str:
    """Encrypt card number using Fernet"""
    return cipher.encrypt(card_number.encode()).decode()


def hash_cvv(cvv: str) -> str:
    """Hash CVV using SHA256 (never store plain text)"""
    return hashlib.sha256(cvv.encode()).hexdigest()


async def seed_database():
    """Main seeding function"""
    
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["biotrust"]
    
    print("🌱 Starting database seeding...\n")
    
    # Load seed data
    data_dir = Path(__file__).parent
    
    with open(data_dir / "seed_merchants.json", "r", encoding="utf-8") as f:
        merchants_data = json.load(f)
    
    with open(data_dir / "seed_users.json", "r", encoding="utf-8") as f:
        users_data = json.load(f)
    
    # Clear existing data
    print("🗑️  Clearing existing collections...")
    await db.merchants.delete_many({})
    await db.users.delete_many({})
    await db.cards.delete_many({})
    await db.transactions.delete_many({})
    print("   ✅ Collections cleared\n")
    
    # Seed merchants
    print("🏪 Seeding merchants...")
    merchants = []
    for merchant_data in merchants_data["merchants"]:
        merchant = {
            **merchant_data,
            "created_at": datetime.utcnow(),
            "total_transactions": 0,
            "total_revenue": 0.0,
            "average_transaction": 0.0,
            "fraud_incidents": 0
        }
        merchants.append(merchant)
    
    result = await db.merchants.insert_many(merchants)
    print(f"   ✅ Inserted {len(result.inserted_ids)} merchants\n")
    
    # Seed users and their cards
    print("👤 Seeding users and cards...")
    for user_data in users_data["users"]:
        # Prepare user document
        cards_data = user_data.pop("cards", [])
        
        # Process cards to store inline
        inline_cards = []
        for card_data in cards_data:
            inline_card = {
                "card_holder": card_data["card_holder"],
                "card_type": card_data["card_type"],
                "card_number": card_data["card_number"],
                "cvv": card_data["cvv"],
                "expiry_month": card_data["expiry_month"],
                "expiry_year": card_data["expiry_year"],
                "is_default": card_data["is_default"],
                "balance": card_data.get("balance", 1000.0),
                "daily_limit": card_data.get("daily_limit", 5000.0),
                "max_transaction": card_data.get("max_transaction", 2000.0),
                "daily_spent": card_data.get("daily_spent", 0.0),
                "last_reset": datetime.utcnow().date().isoformat(),
                "added_at": datetime.utcnow()
            }
            inline_cards.append(inline_card)
        
        user = {
            **user_data,
            "password_hash": hash_password(user_data.pop("password")),
            "cards": inline_cards,  # Store cards inline
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "transactions_today": 0,
            "failed_transactions_last_week": 0,
            "location_history": [],
            "last_transaction_location": None,
            "last_transaction_at": None,
            "liveness_verifications_count": 0
        }
        
        # Insert user with inline cards
        user_result = await db.users.insert_one(user)
        user_id = str(user_result.inserted_id)
        
        print(f"   ✅ Created user: {user_data['name']} ({user_data['email']})")
        
        # Print card info
        for card in inline_cards:
            card_type_emoji = {"visa": "💳", "mastercard": "💳", "amex": "💎"}
            print(f"      {card_type_emoji.get(card['card_type'], '💳')} Card: **** {card['card_number'][-4:]} ({card['card_type'].upper()}) - €{card['balance']:.2f}")
        
        print()
    
    # Create geospatial index for merchants
    print("🗺️  Creating geospatial indexes...")
    await db.merchants.create_index([("location.coordinates", "2dsphere")])
    print("   ✅ Geospatial index created\n")
    
    print("=" * 50)
    print("✨ Database seeding completed successfully!")
    print("=" * 50)
    print(f"\n📊 Summary:")
    print(f"   Merchants: {len(merchants)}")
    print(f"   Users: {len(users_data['users'])}")
    print(f"   Total cards: {sum(len(u.get('cards', [])) for u in users_data['users'])}")
    print(f"\n🔐 Demo credentials (all users):")
    print(f"   Password: password123")
    print(f"\n📧 User emails:")
    for user in users_data["users"]:
        print(f"   - {user['email']}")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(seed_database())
