"""Location routes for real geolocation and reverse geocoding."""

from fastapi import APIRouter, HTTPException, Query
from geopy.geocoders import Nominatim

router = APIRouter()

_geocoder = Nominatim(user_agent="biotrust-location-service")


@router.get("/reverse")
async def reverse_geocode(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
):
    """Resolve coordinates into city/country using OpenStreetMap data."""
    try:
        location = _geocoder.reverse((lat, lon), exactly_one=True, language="pt")
        if not location:
            return {
                "city": "Unknown",
                "country": "Unknown",
                "lat": lat,
                "lon": lon,
            }

        address = location.raw.get("address", {})
        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
            or "Unknown"
        )
        country = address.get("country", "Unknown")

        return {
            "city": city,
            "country": country,
            "lat": lat,
            "lon": lon,
            "provider": "OpenStreetMap/Nominatim",
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Geocoding service unavailable: {exc}")
