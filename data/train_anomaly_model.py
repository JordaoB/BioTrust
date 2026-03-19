"""
Train Anomaly Detection Model
==============================
Script to train the ML model for anomaly detection using historical transaction data

Usage:
    python data/train_anomaly_model.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from backend.config import settings
from src.core.anomaly_detector import anomaly_detector
from datetime import datetime


async def fetch_transactions():
    """Fetch all transactions from MongoDB"""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]
    
    print("\n" + "="*70)
    print("🤖 BioTrust - Anomaly Detection Model Training")
    print("="*70)
    print(f"📊 Fetching transactions from database...")
    
    # Fetch all transactions
    transactions = await db.transactions.find().to_list(length=None)
    
    # Fetch user data to enrich transactions
    users_map = {}
    users = await db.users.find().to_list(length=None)
    for user in users:
        users_map[str(user["_id"])] = user
    
    # Enrich transactions with user context
    enriched_transactions = []
    for tx in transactions:
        user_id = tx.get("user_id")
        user = users_map.get(user_id, {})
        
        # Add user context
        tx_enriched = {
            "amount": tx.get("amount", 0),
            "distance_from_home_km": tx.get("distance_from_home_km", 0),
            "created_at": tx.get("created_at"),
            "average_transaction": user.get("average_transaction", 0),
            "transactions_today": user.get("transactions_today", 0),
            "transactions_last_hour": 0,  # Would need to calculate
            "status": tx.get("status")
        }
        enriched_transactions.append(tx_enriched)
    
    client.close()
    
    print(f"✅ Fetched {len(enriched_transactions)} transactions")
    print(f"📈 Users in database: {len(users_map)}")
    
    return enriched_transactions


async def train_model():
    """Train the anomaly detection model"""
    # Fetch training data
    transactions = await fetch_transactions()
    
    if len(transactions) < 10:
        print("\n⚠️ WARNING: Need at least 10 transactions for training")
        print("   Run 'python data/seed_database.py' to generate sample data")
        print("   Or perform some transactions manually")
        return False
    
    print(f"\n🔧 Training model...")
    print(f"   Algorithm: Isolation Forest")
    print(f"   Features: 10 (amount, time, distance, frequency, etc.)")
    print(f"   Samples: {len(transactions)}")
    
    # Train model
    success = anomaly_detector.train(transactions, contamination=0.05)
    
    if success:
        print("\n✅ Model trained successfully!")
        
        # Show model info
        info = anomaly_detector.get_model_info()
        print(f"\n📊 Model Statistics:")
        stats = info.get("feature_stats", {})
        print(f"   Average Amount: €{stats.get('mean_amount', 0):.2f}")
        print(f"   Std Amount: €{stats.get('std_amount', 0):.2f}")
        print(f"   Average Distance: {stats.get('mean_distance', 0):.1f}km")
        print(f"   Max TX/Day: {stats.get('max_transactions_per_day', 0)}")
        print(f"   Amount Range: €{stats.get('typical_amount_range', (0,0))[0]:.0f} - €{stats.get('typical_amount_range', (0,0))[1]:.0f}")
        
        print(f"\n💾 Model saved to: models/anomaly_detector.pkl")
        print(f"🚀 Model is ready for use in the API")
        print("\n" + "="*70)
        
        return True
    else:
        print("\n❌ Failed to train model")
        return False


def main():
    """Main entry point"""
    try:
        asyncio.run(train_model())
    except KeyboardInterrupt:
        print("\n\n⚠️ Training interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during training: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
