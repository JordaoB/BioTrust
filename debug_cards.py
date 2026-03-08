import httpx
import asyncio
import json

async def debug_cards():
    async with httpx.AsyncClient() as client:
        # Get user
        response = await client.get("http://localhost:8000/api/users/email/joao.silva@example.com")
        user = response.json()
        print(f"User ID: {user['_id']}")
        
        # Get cards
        response = await client.get(f"http://localhost:8000/api/users/{user['_id']}/cards")
        cards = response.json()
        print(f"\nCards: {json.dumps(cards, indent=2)}")
        
        if cards:
            print(f"\nCard ID to use: {cards[0]['id']}")

asyncio.run(debug_cards())
