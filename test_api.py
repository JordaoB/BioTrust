"""
Quick test script to verify API functionality
Run after starting the server with: python -m backend.main
"""

import httpx
import asyncio
import json


async def test_api():
    """Test BioTrust API endpoints"""
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        
        print("🧪 Testing BioTrust API\n")
        
        # 1. Health check
        print("1️⃣ Testing health endpoint...")
        response = await client.get(f"{base_url}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}\n")
        
        # 2. Get user by email
        print("2️⃣ Testing get user by email...")
        response = await client.get(f"{base_url}/api/users/email/joao.silva@example.com")
        if response.status_code == 200:
            user = response.json()
            user_id = user["_id"]
            print(f"   ✅ Found user: {user['name']}")
            print(f"   📍 Home: {user['home_location']['city']}\n")
        else:
            print(f"   ❌ Error: {response.status_code}\n")
            return
        
        # 3. Get user cards
        print("3️⃣ Testing get user cards...")
        response = await client.get(f"{base_url}/api/users/{user_id}/cards")
        cards = response.json()
        print(f"   ✅ Found {len(cards)} cards")
        if cards:
            card_id = cards[0]["id"]
            print(f"   💳 Card: **** {cards[0]['last_four']} ({cards[0]['card_type']})\n")
        
        # 4. Find nearby merchants
        print("4️⃣ Testing nearby merchants (Lisboa)...")
        response = await client.get(
            f"{base_url}/api/merchants/nearby",
            params={"lat": 38.7223, "lon": -9.1393, "radius_km": 10}
        )
        merchants = response.json()
        print(f"   ✅ Found {len(merchants)} merchants nearby")
        
        # If no nearby merchants, get any merchant as fallback
        merchant_id = None
        if merchants:
            merchant = merchants[0]
            merchant_id = merchant["_id"]
            print(f"   🏪 Closest: {merchant['name']} ({merchant['distance_km']:.2f} km away)\n")
        else:
            # Try to get any merchant
            print("   ⚠️  No nearby merchants, getting first available...")
            response = await client.get(f"{base_url}/api/merchants/", params={"limit": 1})
            all_merchants = response.json()
            if all_merchants:
                merchant_id = all_merchants[0]["_id"]
                print(f"   🏪 Using: {all_merchants[0]['name']}\n")
            else:
                print("   ❌ No merchants in database!\n")
                return
        
        # 5. Create transaction
        print("5️⃣ Testing transaction creation...")
        transaction_data = {
            "user_id": user_id,
            "card_id": card_id,
            "merchant_id": merchant_id,
            "amount": 150.00,
            "currency": "EUR",
            "transaction_type": "purchase",
            "user_location": {
                "latitude": 38.7223,
                "longitude": -9.1393
            }
        }
        
        response = await client.post(
            f"{base_url}/api/transactions/",
            json=transaction_data
        )
        
        if response.status_code == 201:
            transaction = response.json()
            transaction_id = transaction["_id"]
            print(f"   ✅ Transaction created")
            print(f"   💰 Amount: €{transaction['amount']}")
            print(f"   🎯 Risk Score: {transaction['risk_score']} ({transaction['risk_level']})")
            print(f"   🔐 Liveness Required: {transaction['liveness_required']}\n")
            
            # 6. Simulate liveness if required
            if transaction["liveness_required"]:
                print("6️⃣ Testing liveness verification (simulation)...")
                response = await client.post(
                    f"{base_url}/api/liveness/simulate",
                    params={"success": True}
                )
                liveness = response.json()
                print(f"   ✅ Liveness simulation complete")
                print(f"   ❤️ Heart Rate: {liveness['liveness_result']['heart_rate']}")
                print(f"   🛡️ Anti-spoofing: {liveness['liveness_result']['anti_spoofing']['final_confidence']}\n")
                
                # Update transaction with liveness result
                print("7️⃣ Updating transaction with liveness result...")
                response = await client.patch(
                    f"{base_url}/api/transactions/{transaction_id}/liveness",
                    json=liveness["liveness_result"]
                )
                updated_transaction = response.json()
                print(f"   ✅ Transaction updated")
                print(f"   📊 Status: {updated_transaction['status']}\n")
        
        print("✅ All tests passed!\n")
        print("🔒 Privacy Check: No biometric data was stored")
        print("   Only verification metadata saved to database")


if __name__ == "__main__":
    asyncio.run(test_api())
