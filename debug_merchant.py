from pymongo import MongoClient
import json

client = MongoClient("mongodb://localhost:27017")
db = client.biotrust

merchant = db.merchants.find_one()
print("Merchant structure:")
print(json.dumps(merchant, indent=2, default=str))

print("\n\nLocation field:")
print(merchant.get("location"))

client.close()
