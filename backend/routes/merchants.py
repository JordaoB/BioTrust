"""
Merchants API Routes
Find merchants by location and category
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from backend.database import get_database
from backend.models.merchant import Merchant, MerchantSearchResult


def serialize_doc(doc):
    """Convert MongoDB ObjectId to string"""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


router = APIRouter()


@router.get("/nearby", response_model=List[MerchantSearchResult])
async def get_nearby_merchants(
    lat: float = Query(..., description="User latitude"),
    lon: float = Query(..., description="User longitude"),
    radius_km: float = Query(5.0, description="Search radius in km", ge=0.1, le=50),
    category: Optional[str] = None,
    db=Depends(get_database)
):
    """
    Find merchants near a location using MongoDB geospatial queries
    Uses 2dsphere index on location.coordinates
    """
    
    # Build aggregation pipeline
    pipeline = [
        {
            "$geoNear": {
                "near": {
                    "type": "Point",
                    "coordinates": [lon, lat]  # GeoJSON: [longitude, latitude]
                },
                "distanceField": "distance_meters",
                "maxDistance": radius_km * 1000,  # Convert km to meters
                "spherical": True
            }
        }
    ]
    
    # Filter by category if provided
    if category:
        pipeline.append({
            "$match": {"category": category}
        })
    
    # Add distance in km
    pipeline.append({
        "$addFields": {
            "distance_km": {"$divide": ["$distance_meters", 1000]}
        }
    })
    
    # Sort by distance
    pipeline.append({"$sort": {"distance_meters": 1}})
    
    # Execute aggregation
    cursor = db.merchants.aggregate(pipeline)
    merchants = await cursor.to_list(length=100)
    
    return [serialize_doc(m) for m in merchants]


@router.get("/{merchant_id}", response_model=Merchant)
async def get_merchant(merchant_id: str, db=Depends(get_database)):
    """Get merchant by ID"""
    merchant = await db.merchants.find_one({"_id": merchant_id})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return serialize_doc(merchant)


@router.get("/category/{category}", response_model=List[Merchant])
async def get_merchants_by_category(
    category: str,
    skip: int = 0,
    limit: int = 20,
    db=Depends(get_database)
):
    """Get all merchants in a category"""
    cursor = db.merchants.find(
        {"category": category}
    ).skip(skip).limit(limit)
    
    merchants = await cursor.to_list(length=limit)
    
    if not merchants:
        raise HTTPException(status_code=404, detail=f"No merchants found in category: {category}")
    
    return [serialize_doc(m) for m in merchants]


@router.get("/city/{city}", response_model=List[Merchant])
async def get_merchants_by_city(
    city: str,
    db=Depends(get_database)
):
    """Get all merchants in a city"""
    merchants = await db.merchants.find(
        {"location.city": city}
    ).to_list(length=100)
    
    if not merchants:
        raise HTTPException(status_code=404, detail=f"No merchants found in city: {city}")
    
    return [serialize_doc(m) for m in merchants]


@router.get("/", response_model=List[Merchant])
async def list_merchants(
    skip: int = 0,
    limit: int = 20,
    db=Depends(get_database)
):
    """List all merchants (paginated)"""
    cursor = db.merchants.find().skip(skip).limit(limit)
    merchants = await cursor.to_list(length=limit)
    return [serialize_doc(m) for m in merchants]
