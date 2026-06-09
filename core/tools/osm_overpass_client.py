import logging
import os
from typing import Dict, List, Sequence

import requests

logger = logging.getLogger(__name__)


_DEFAULT_ENDPOINTS: Sequence[str] = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
)


class OSMOverpassClient:
    _user_agent = "travel-agent-pipeline/1.0 (contact: travel-agent@example.com)"

    def __init__(
        self,
        endpoints: Sequence[str] | None = None,
        timeout_seconds: float | None = None,
    ):
        custom = os.getenv("OVERPASS_ENDPOINTS")
        if custom:
            parsed = tuple(item.strip() for item in custom.split(",") if item.strip())
        else:
            parsed = None
        self.endpoints: Sequence[str] = endpoints or parsed or _DEFAULT_ENDPOINTS
        self.timeout_seconds = timeout_seconds or float(os.getenv("OVERPASS_TIMEOUT_SECONDS", "21"))

    def search_combined(
        self,
        lat: float,
        lon: float,
        radius_m: int,
        categories: Sequence[str],
        limit_per_category: int = 10,
    ) -> Dict[str, List[Dict]]:
        query = self._build_combined_query(lat, lon, radius_m, categories)
        elements = self._post_with_failover(query)
        grouped: Dict[str, List[Dict]] = {category: [] for category in categories}
        for element in elements:
            tags = element.get("tags", {})
            category = self._classify(tags, categories)
            if not category:
                continue
            normalized = self._normalize_item(element, lat, lon, category)
            if normalized.get("name"):
                grouped[category].append(normalized)
        for category, items in grouped.items():
            items.sort(key=lambda item: item["distance_m"])
            grouped[category] = items[:limit_per_category]
        return grouped

    def _post_with_failover(self, query: str) -> List[Dict]:
        last_error: Exception | None = None
        for endpoint in self.endpoints:
            try:
                response = requests.post(
                    endpoint,
                    data={"data": query},
                    timeout=self.timeout_seconds,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": self._user_agent,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                return payload.get("elements", [])
            except Exception as exc:
                last_error = exc
                logger.warning("Overpass endpoint failed (%s): %s", endpoint, exc)
                continue
        if last_error:
            raise last_error
        return []

    def _build_combined_query(
        self,
        lat: float,
        lon: float,
        radius_m: int,
        categories: Sequence[str],
    ) -> str:
        selectors: List[str] = []
        for category in categories:
            if category == "hotels":
                selectors.append(f'node(around:{radius_m},{lat},{lon})["tourism"="hotel"];')
            elif category == "restaurants":
                selectors.append(f'node(around:{radius_m},{lat},{lon})["amenity"="restaurant"];')
            elif category == "attractions":
                selectors.extend(
                    [
                        f'node(around:{radius_m},{lat},{lon})["tourism"="attraction"];',
                        f'node(around:{radius_m},{lat},{lon})["historic"];',
                        f'node(around:{radius_m},{lat},{lon})["museum"];',
                    ]
                )
        body = "".join(selectors)
        return f"[out:json][timeout:25];({body});out body;"

    @staticmethod
    def _classify(tags: Dict, categories: Sequence[str]) -> str | None:
        if "hotels" in categories and tags.get("tourism") == "hotel":
            return "hotels"
        if "restaurants" in categories and tags.get("amenity") == "restaurant":
            return "restaurants"
        if "attractions" in categories and (
            tags.get("tourism") == "attraction" or "historic" in tags or "museum" in tags
        ):
            return "attractions"
        return None

    def _normalize_item(self, element: Dict, lat: float, lon: float, category: str) -> Dict:
        tags = element.get("tags", {})
        item_lat = element.get("lat")
        item_lon = element.get("lon")
        return {
            "name": (tags.get("name") or "").strip(),
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
