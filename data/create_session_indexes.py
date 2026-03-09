"""
MongoDB Session Indexes
Creates indexes for optimal session lookup performance
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

# MongoDB configuration
MONGO_URI = "mongodb://localhost:27017"
DATABASE_NAME = "biotrust"


async def create_session_indexes():
    """Create indexes for sessions collection"""
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DATABASE_NAME]
    
    print("Creating session indexes...")
    
    # Index on access_token for fast lookup during authentication
    await db.sessions.create_index("access_token", unique=True)
    print("✅ Created index: access_token (unique)")
    
    # Index on refresh_token for token refresh operations
    await db.sessions.create_index("refresh_token", unique=True)
    print("✅ Created index: refresh_token (unique)")
    
    # Index on user_id for listing user sessions
    await db.sessions.create_index("user_id")
    print("✅ Created index: user_id")
    
    # Compound index on is_active and user_id for active sessions query
    await db.sessions.create_index([("user_id", 1), ("is_active", 1)])
    print("✅ Created compound index: user_id + is_active")
    
    # TTL index on refresh_token_expires_at for automatic cleanup
    # Sessions will be automatically deleted 1 day after refresh token expires
    await db.sessions.create_index(
        "refresh_token_expires_at", 
        expireAfterSeconds=86400  # 24 hours
    )
    print("✅ Created TTL index: refresh_token_expires_at (auto-cleanup)")
    
    # List all indexes
    indexes = await db.sessions.list_indexes().to_list(length=None)
    print("\n📋 All session indexes:")
    for idx in indexes:
        print(f"   - {idx['name']}: {idx.get('key', {})}")
    
    client.close()
    print("\n✅ Session indexes created successfully!")


async def main():
    await create_session_indexes()


if __name__ == "__main__":
    asyncio.run(main())
