"""
normalisation/geocoder.py
Converts parsed addresses to lat/lng using self-hosted Nominatim.

Quality levels:
  HIGH   — street/building level match
  MEDIUM — suburb/neighbourhood/locality level
  LOW    — pin code centroid fallback
  FAILED — no coordinates available
"""
import os
import requests
from typing import Optional

NOMINATIM_URL = os.getenv("NOMINATIM_URL", "http://localhost:8080")
NOMINATIM_TIMEOUT = 3   # seconds

# Pin code centroids (fallback when Nominatim is unavailable or returns
# LOW quality)
PIN_CENTROIDS = {
    "560058": (13.0287, 77.5201),   # Peenya Industrial Area
    "560073": (12.9952, 77.5527),   # Rajajinagar
    "560032": (13.0180, 77.5430),   # Yeshwanthpur
    "560022": (13.0236, 77.5350),   # Peenya
    "560010": (12.9855, 77.5493),   # Rajajinagar
    "560086": (12.9726, 77.5318),   # Vijayanagar
    "560040": (13.0030, 77.5480),   # Basaveshwaranagar
    "560057": (13.0260, 77.5180),   # Peenya
}

# OSM types that indicate each quality level
HIGH_QUALITY_TYPES = {"road", "house", "building", "amenity", "office"}
MEDIUM_QUALITY_TYPES = {
    "suburb",
    "neighbourhood",
    "quarter",
    "village",
    "town",
    "city_block"}


def geocode_address(parsed_address) -> dict:
    """
    Input:  a ParsedAddress dataclass instance.
    Output: {lat: float|None, lng: float|None, quality: str}

    Tries Nominatim first. Falls back to pin code centroid.
    """
    if parsed_address is None:
        return {"lat": None, "lng": None, "quality": "FAILED"}

    # Build Nominatim query from most specific to least specific components
    query_parts = []
    if parsed_address.street:
        query_parts.append(parsed_address.street)
    if parsed_address.locality:
        query_parts.append(parsed_address.locality)
    if parsed_address.industrial_area:
        query_parts.append(parsed_address.industrial_area)
    if parsed_address.district:
        query_parts.append(parsed_address.district)
    if parsed_address.pin_code:
        query_parts.append(parsed_address.pin_code)
    query_parts.append("Karnataka, India")

    query = ", ".join(query_parts)

    # Try Nominatim
    try:
        response = requests.get(
            f"{NOMINATIM_URL}/search",
            params={
                "q": query,
                "format": "json",
                "limit": 1,
                "countrycodes": "in",
                "addressdetails": 1,
            },
            timeout=NOMINATIM_TIMEOUT,
        )
        results = response.json()
        if results:
            result = results[0]
            lat = float(result["lat"])
            lon = float(result["lon"])
            osm_type = result.get("type", "")

            if osm_type in HIGH_QUALITY_TYPES:
                quality = "HIGH"
            elif osm_type in MEDIUM_QUALITY_TYPES:
                quality = "MEDIUM"
            else:
                quality = "LOW"

            return {"lat": lat, "lng": lon, "quality": quality}
    except Exception:
        pass  # Nominatim unavailable — fall through to centroid

    # Fallback: pin code centroid
    if parsed_address.pin_code and parsed_address.pin_code in PIN_CENTROIDS:
        lat, lng = PIN_CENTROIDS[parsed_address.pin_code]
        return {"lat": lat, "lng": lng, "quality": "LOW"}

    return {"lat": None, "lng": None, "quality": "FAILED"}
