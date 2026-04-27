import os
from typing import Dict, List

import requests


class OSMOverpassClient:
    def __init__(self, endpoint: str | None = None, timeout_seconds: float | None = None):
        self.endpoint = endpoint or os.getenv("OVERPASS_ENDPOINT", "https://overpass-api.de/api/interpreter")
        self.timeout_seconds = timeout_seconds or float(os.getenv("OVERPASS_TIMEOUT_SECONDS", "7"))

    def search(self, lat: float, lon: float, radius_m: int, category: str, limit: int = 8) -> List[Dict]:
        query = self._build_query(lat, lon, radius_m, category)
        response = requests.post(
            self.endpoint,
            data={"data": query},
            timeout=self.timeout_seconds,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("elements", [])
        normalized = [self._normalize_item(item, lat, lon, category) for item in items]
        normalized = [item for item in normalized if item.get("name")]
        normalized.sort(key=lambda item: item["distance_m"])
        return normalized[:limit]

    def _build_query(self, lat: float, lon: float, radius_m: int, category: str) -> str:
        if category == "hotels":
            selector = 'node(around:{radius},{lat},{lon})["tourism"="hotel"];'
        elif category == "restaurants":
            selector = 'node(around:{radius},{lat},{lon})["amenity"="restaurant"];'
        else:
            selector = (
                'node(around:{radius},{lat},{lon})["tourism"="attraction"];'
                'node(around:{radius},{lat},{lon})["historic"];'
                'node(around:{radius},{lat},{lon})["museum"];'
            )
        return (
            "[out:json][timeout:25];("
            + selector.format(radius=radius_m, lat=lat, lon=lon)
            + ");out body;"
        )

    def _normalize_item(self, item: Dict, lat: float, lon: float, category: str) -> Dict:
        tags = item.get("tags", {})
        item_lat = item.get("lat")
        item_lon = item.get("lon")
        return {
            "name": tags.get("name", "").strip(),
            "category": category,
            "lat": item_lat,
            "lon": item_lon,
            "distance_m": self._distance_m(lat, lon, item_lat, item_lon),
            "phone": (tags.get("contact:phone") or tags.get("phone") or "").strip() or None,
            "address": tags.get("addr:full") or tags.get("addr:street"),
            "source": "osm_overpass",
        }

    @staticmethod
    def _distance_m(lat1: float, lon1: float, lat2: float | None, lon2: float | None) -> float:
        if lat2 is None or lon2 is None:
            return 999999.0
        dx = (lon2 - lon1) * 111320.0
        dy = (lat2 - lat1) * 110540.0
        return (dx * dx + dy * dy) ** 0.5
