"""
Migration Script: Add balance and limits to existing cards
Converts existing user cards to include balance, daily_limit, max_transaction
"""

from pymongo import MongoClient
from datetime import datetime


def migrate_cards():
    """Add financial fields to existing cards"""
    
    # Connect to MongoDB
    client = MongoClient("mongodb://localhost:27017")
    db = client["biotrust"]
    
    print("🔄 Starting card balance migration...\n")
    
    # Get all users
    users = list(db.users.find({}))
    
    updated_count = 0
    for user in users:
        cards = user.get("cards", [])
        
        if not cards:
            continue
        
        # Update each card with new fields if they don't exist
        updated_cards = []
        for card in cards:
            # Add new fields if missing
            if "balance" not in card:
                card["balance"] = 1000.0  # Default balance
            if "daily_limit" not in card:
                card["daily_limit"] = 5000.0
            if "max_transaction" not in card:
                card["max_transaction"] = 2000.0
            if "daily_spent" not in card:
                card["daily_spent"] = 0.0
            if "last_reset" not in card:
                card["last_reset"] = datetime.utcnow().date().isoformat()
            
            updated_cards.append(card)
        
        # Update user document
        db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"cards": updated_cards}}
        )
        
        print(f"✅ Updated {len(cards)} cards for user: {user.get('name', user.get('email', 'Unknown'))}")
        updated_count += 1
    
    print(f"\n✨ Migration completed successfully!")
    print(f"   Updated {updated_count} users")
    
    client.close()


if __name__ == "__main__":
    migrate_cards()
