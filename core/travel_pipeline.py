from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from core.location_resolver import LocationResult
from core.tools.openmeteo_client import OpenMeteoClient
from core.tools.opentripmap_client import OpenTripMapClient
from core.tools.osm_overpass_client import OSMOverpassClient


@dataclass(frozen=True)
class TravelContext:
    location: LocationResult
    date_str: str


@dataclass
class SectionResults:
    weather: Optional[Dict] = None
    hotels: List[Dict] = field(default_factory=list)
    restaurants: List[Dict] = field(default_factory=list)
    attractions: List[Dict] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "weather": self.weather,
            "hotels": self.hotels,
            "restaurants": self.restaurants,
            "attractions": self.attractions,
            "errors": self.errors,
        }


class TTLCache:
    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds
        self._store: Dict[str, tuple[float, object]] = {}

    def get(self, key: str):
        value = self._store.get(key)
        if not value:
            return None
        expires_at, payload = value
        if time.time() > expires_at:
            self._store.pop(key, None)
            return None
        return payload

    def set(self, key: str, payload):
        self._store[key] = (time.time() + self.ttl_seconds, payload)


class TravelPipeline:
    def __init__(self):
        self.overpass = OSMOverpassClient()
        self.openmeteo = OpenMeteoClient()
        self.opentripmap = OpenTripMapClient()
        self.tool_timeout_seconds = float(os.getenv("TRAVEL_TOOL_TIMEOUT_SECONDS", "8"))
        self.global_timeout_seconds = float(os.getenv("TRAVEL_GLOBAL_TIMEOUT_SECONDS", "15"))
        self.search_radius_m = int(os.getenv("TRAVEL_SEARCH_RADIUS_M", "4000"))
        self.weather_cache = TTLCache(ttl_seconds=int(os.getenv("TRAVEL_WEATHER_CACHE_TTL_SECONDS", "1800")))
        self.place_cache = TTLCache(ttl_seconds=int(os.getenv("TRAVEL_PLACES_CACHE_TTL_SECONDS", "1800")))

    async def run(
        self,
        context: TravelContext,
        on_event: Optional[Callable[[str, Dict], None]] = None,
    ) -> SectionResults:
        results = SectionResults()
        if on_event:
            on_event("location_resolved", {"location": context.location.to_dict(), "date": context.date_str})

        tasks = {
            "weather_ready": asyncio.create_task(self._load_weather(context)),
            "hotels_ready": asyncio.create_task(self._load_places(context, "hotels")),
            "restaurants_ready": asyncio.create_task(self._load_places(context, "restaurants")),
            "attractions_ready": asyncio.create_task(self._load_attractions(context)),
        }

        try:
            done, pending = await asyncio.wait(
                tasks.values(), timeout=self.global_timeout_seconds, return_when=asyncio.ALL_COMPLETED
            )
            for task in pending:
                task.cancel()
        except Exception as exc:
            results.errors["pipeline"] = str(exc)
            return results

        name_by_task = {task: event_name for event_name, task in tasks.items()}
        for task in done:
            event_name = name_by_task[task]
            try:
                payload = task.result()
                if event_name == "weather_ready":
                    results.weather = payload
                elif event_name == "hotels_ready":
                    results.hotels = payload
                elif event_name == "restaurants_ready":
                    results.restaurants = payload
                elif event_name == "attractions_ready":
                    results.attractions = payload
                if on_event:
                    on_event(event_name, payload if isinstance(payload, dict) else {"items": payload})
            except Exception as exc:
                results.errors[event_name] = str(exc)
                if on_event:
                    on_event(event_name, {"error": str(exc)})

        for event_name, task in tasks.items():
            if task.cancelled():
                results.errors[event_name] = "timed out"
                if on_event:
                    on_event(event_name, {"error": "timed out"})

        if on_event:
            on_event("final_ready", results.to_dict())
        return results

    async def _load_weather(self, context: TravelContext) -> Dict:
        key = f"{context.location.lat:.4f}:{context.location.lon:.4f}:{context.date_str}"
        cached = self.weather_cache.get(key)
        if cached:
            return cached
        weather = await asyncio.wait_for(
            asyncio.to_thread(
                self.openmeteo.get_daily_forecast,
                context.location.lat,
                context.location.lon,
                context.date_str,
            ),
            timeout=self.tool_timeout_seconds,
        )
        self.weather_cache.set(key, weather)
        return weather

    async def _load_places(self, context: TravelContext, category: str) -> List[Dict]:
        key = (
            f"{category}:{context.location.lat:.4f}:{context.location.lon:.4f}:"
            f"{self.search_radius_m}"
        )
        cached = self.place_cache.get(key)
        if cached:
            return cached

        places = await asyncio.wait_for(
            asyncio.to_thread(
                self.overpass.search,
                context.location.lat,
                context.location.lon,
                self.search_radius_m,
                category,
                10,
            ),
            timeout=self.tool_timeout_seconds,
        )
        ranked = self._rank_places(places)
        self.place_cache.set(key, ranked)
        return ranked

    async def _load_attractions(self, context: TravelContext) -> List[Dict]:
        key = (
            f"attractions:{context.location.lat:.4f}:{context.location.lon:.4f}:"
            f"{self.search_radius_m}"
        )
        cached = self.place_cache.get(key)
        if cached:
            return cached

        attractions = await asyncio.wait_for(
            asyncio.to_thread(
                self.overpass.search,
                context.location.lat,
                context.location.lon,
                self.search_radius_m,
                "attractions",
                12,
            ),
            timeout=self.tool_timeout_seconds,
        )
        if len(attractions) < 3 and self.opentripmap.is_enabled():
            fallback = await asyncio.wait_for(
                asyncio.to_thread(
                    self.opentripmap.find_attractions,
                    context.location.lat,
                    context.location.lon,
                    self.search_radius_m,
                    8,
                ),
                timeout=self.tool_timeout_seconds,
            )
            attractions.extend(fallback)
        ranked = self._rank_places(attractions)
        self.place_cache.set(key, ranked)
        return ranked

    @staticmethod
    def _rank_places(places: List[Dict]) -> List[Dict]:
        ranked = []
        seen = set()
        for item in places:
            name = (item.get("name") or "").strip().lower()
            if not name or name in seen:
                continue
            seen.add(name)
            phone = item.get("phone")
            if not phone:
                item["phone"] = None
            ranked.append(item)
        ranked.sort(
            key=lambda p: (
                0 if p.get("phone") else 1,
                p.get("distance_m", 999999.0),
            )
        )
        return ranked[:5]
