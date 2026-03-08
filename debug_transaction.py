import httpx
import asyncio
import json

async def test_transaction():
    async with httpx.AsyncClient() as client:
        # Get user and card
        response = await client.get("http://localhost:8000/api/users/email/joao.silva@example.com")
        user = response.json()
        user_id = user['_id']
        
        response = await client.get(f"http://localhost:8000/api/users/{user_id}/cards")
        cards = response.json()
        card_id = cards[0]['id']
        
        # Get merchant
        response = await client.get("http://localhost:8000/api/merchants/", params={"limit": 1})
        merchants = response.json()
        merchant_id = merchants[0]['_id']
        
        print(f"User ID: {user_id}")
        print(f"Card ID: {card_id}")
        print(f"Merchant ID: {merchant_id}\n")
        
        # Try creating transaction
        tx_data = {
            "user_id": user_id,
            "card_id": card_id,
            "merchant_id": merchant_id,
            "amount": 25.00,
            "currency": "EUR",
            "type": "physical",
            "user_location": {
                "lat": 38.7223,
                "lon": -9.1393
            }
        }
        
        print("Posting transaction...")
        print(json.dumps(tx_data, indent=2))
        
        response = await client.post("http://localhost:8000/api/transactions/", json=tx_data)
        
        print(f"\nStatus: {response.status_code}")
        if response.status_code != 201:
            print("Error response:")
            print(response.text)
        else:
            print("Success!")
            print(json.dumps(response.json(), indent=2))

asyncio.run(test_transaction())
