"""
Simple Database Seeding Script (Synchronous)
Populates MongoDB with seed users from seed_users.json
"""

import json
import hashlib
from pathlib import Path
from pymongo import MongoClient

def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def seed_database():
    """Seed database with users"""
    
    # Connect to MongoDB
    client = MongoClient("mongodb://localhost:27017")
    db = client["biotrust"]
    
    print("🌱 Starting database seeding...\n")
    
    # Load seed users
    data_dir = Path(__file__).parent
    with open(data_dir / "seed_users.json", "r", encoding="utf-8") as f:
        users_data = json.load(f)
    
    # Clear existing users
    print("🗑️  Clearing existing users...")
    result = db.users.delete_many({})
    print(f"   Deleted {result.deleted_count} existing users\n")
    
    # Insert users with cards and balance
    print("👥 Inserting users...")
    for user in users_data["users"]:
        # Hash password
        user["password_hash"] = hash_password(user["password"])
        del user["password"]  # Remove plain password
        
        # Add balance field (€1000 default)
        user["balance"] = 1000.0
        
        # Process cards if they exist
        if "cards" in user and user["cards"]:
            for card in user["cards"]:
                # Add created_at timestamp
                card["created_at"] = "2026-03-08T00:00:00"
                # Format expiry as MM/YY
                card["expiry"] = f"{card['expiry_month']:02d}/{str(card['expiry_year'])[-2:]}"
                # Create masked number
                card_num = card["card_number"]
                card["masked_number"] = f"**** **** **** {card_num[-4:]}"
                card["last_four"] = card_num[-4:]
        
        # Insert user
        result = db.users.insert_one(user)
        print(f"   ✓ {user['name']} ({user['email']}) - {len(user.get('cards', []))} card(s)")
    
    print(f"\n✅ Seeding complete!")
    print(f"   Total users: {db.users.count_documents({})}")
    
    # List all users
    print("\n📋 Registered users:")
    for user in db.users.find({}, {"name": 1, "email": 1, "balance": 1, "cards": 1}):
        cards_count = len(user.get("cards", []))
        print(f"   • {user['name']} - {user['email']} - €{user.get('balance', 0):.2f} - {cards_count} card(s)")
    
    client.close()

if __name__ == "__main__":
    seed_database()
