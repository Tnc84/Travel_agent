import os
from typing import Dict, List

import requests


class OpenTripMapClient:
    def __init__(self, api_key: str | None = None, timeout_seconds: float | None = None):
        self.api_key = api_key or os.getenv("OPENTRIPMAP_API_KEY", "")
        self.timeout_seconds = timeout_seconds or float(os.getenv("OPENTRIPMAP_TIMEOUT_SECONDS", "6"))
        self.radius_endpoint = "https://api.opentripmap.com/0.1/en/places/radius"

    def is_enabled(self) -> bool:
        return bool(self.api_key)

    def find_attractions(self, lat: float, lon: float, radius_m: int, limit: int = 8) -> List[Dict]:
        if not self.is_enabled():
            return []
        params = {
            "apikey": self.api_key,
            "lat": lat,
            "lon": lon,
            "radius": radius_m,
            "kinds": "interesting_places,architecture,museums,historic",
            "limit": limit,
            "rate": 2,
            "format": "json",
        }
        response = requests.get(self.radius_endpoint, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        results = []
        for item in payload:
            results.append(
                {
                    "name": (item.get("name") or "").strip(),
                    "category": "attractions",
                    "lat": item.get("point", {}).get("lat"),
                    "lon": item.get("point", {}).get("lon"),
                    "distance_m": item.get("dist") or 999999.0,
                    "phone": None,
                    "address": None,
                    "source": "open_trip_map",
                }
            )
        return [item for item in results if item.get("name")]
