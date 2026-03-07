"""
MongoDB Database Connection
Motor (async MongoDB driver) connection and utilities
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import GEOSPHERE
from backend.config import settings
import logging

logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB connection manager"""
    
    client: AsyncIOMotorClient = None
    db = None
    

mongodb = MongoDB()


async def connect_to_mongo():
    """Connect to MongoDB on startup"""
    logger.info("Connecting to MongoDB...")
    mongodb.client = AsyncIOMotorClient(settings.MONGODB_URL)
    mongodb.db = mongodb.client[settings.MONGODB_DB_NAME]
    
    # Create indexes
    await create_indexes()
    
    logger.info(f"Connected to MongoDB database: {settings.MONGODB_DB_NAME}")


async def close_mongo_connection():
    """Close MongoDB connection on shutdown"""
    logger.info("Closing MongoDB connection...")
    mongodb.client.close()


async def create_indexes():
    """Create database indexes for performance"""
    logger.info("Creating database indexes...")
    
    # Users collection
    await mongodb.db.users.create_index("email", unique=True)
    await mongodb.db.users.create_index("phone")
    
    # Cards collection
    await mongodb.db.cards.create_index("user_id")
    await mongodb.db.cards.create_index("last_four")
    
    # Transactions collection
    await mongodb.db.transactions.create_index("user_id")
    await mongodb.db.transactions.create_index("card_id")
    await mongodb.db.transactions.create_index("created_at")
    await mongodb.db.transactions.create_index([("user_id", 1), ("created_at", -1)])
    
    # Merchants collection - GEOSPATIAL INDEX for location queries
    await mongodb.db.merchants.create_index([("location.coordinates", GEOSPHERE)])
    await mongodb.db.merchants.create_index("category")
    await mongodb.db.merchants.create_index("location.city")
    
    logger.info("Indexes created successfully")


def get_database():
    """Dependency to get database instance"""
    return mongodb.db
