from __future__ import annotations

import concurrent.futures
import logging
from typing import Sequence

from core.services.travel.cache import TTLCache
from core.services.travel.results import PoiData, ServiceError, ServiceErrorKind, ServiceResult
from core.tools.opentripmap_client import OpenTripMapClient
from core.tools.osm_overpass_client import OSMOverpassClient

logger = logging.getLogger(__name__)

_CATEGORIES: Sequence[str] = ("hotels", "restaurants", "attractions")
_MIN_ATTRACTIONS_FOR_FALLBACK = 3
_LIMIT_PER_CATEGORY = 12
_FALLBACK_LIMIT = 8


class PoiService:
    def __init__(
        self,
        overpass: OSMOverpassClient,
        opentripmap: OpenTripMapClient,
        cache: TTLCache,
        timeout_seconds: float,
        search_radius_m: int,
    ):
        self._overpass = overpass
        self._opentripmap = opentripmap
        self._cache = cache
        self._timeout_seconds = timeout_seconds
        self._search_radius_m = search_radius_m

    def fetch(
        self,
        lat: float,
        lon: float,
        radius_m: int | None = None,
    ) -> ServiceResult[PoiData]:
        radius = radius_m if radius_m is not None else self._search_radius_m
        cache_key = f"osm_combined:{lat:.4f}:{lon:.4f}:{radius}"
        grouped = self._cache.get(cache_key)

        if grouped is None:
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(
                        self._overpass.search_combined,
                        lat,
                        lon,
                        radius,
                        _CATEGORIES,
                        _LIMIT_PER_CATEGORY,
                    )
                    grouped = future.result(timeout=self._timeout_seconds)
                self._cache.set(cache_key, grouped)
            except concurrent.futures.TimeoutError:
                logger.warning("PoiService overpass timeout")
                return ServiceResult.failure(
                    ServiceError(
                        ServiceErrorKind.TIMEOUT,
                        "overpass timed out",
                        provider="osm_overpass",
                    )
                )
            except Exception as exc:
                logger.warning("PoiService overpass failed: %s", exc)
                return ServiceResult.failure(
                    ServiceError(
                        ServiceErrorKind.PROVIDER_UNAVAILABLE,
                        f"{type(exc).__name__}: {exc}",
                        provider="osm_overpass",
                    )
                )

        hotels = list(grouped.get("hotels", []))
        restaurants = list(grouped.get("restaurants", []))
        attractions = list(grouped.get("attractions", []))
        fallback_errors: dict[str, ServiceError] = {}

        if len(attractions) < _MIN_ATTRACTIONS_FOR_FALLBACK and self._opentripmap.is_enabled():
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(
                        self._opentripmap.find_attractions,
                        lat,
                        lon,
                        radius,
                        _FALLBACK_LIMIT,
                    )
                    fallback = future.result(timeout=self._timeout_seconds)
                attractions.extend(fallback)
            except Exception as exc:
                logger.warning("OpenTripMap fallback failed: %s", exc)
                fallback_errors["fetch_poi_fallback"] = ServiceError(
                    ServiceErrorKind.PROVIDER_UNAVAILABLE,
                    f"{type(exc).__name__}: {exc}",
                    provider="open_trip_map",
                )

        return ServiceResult.success(
            PoiData(
                hotels=hotels,
                restaurants=restaurants,
                attractions=attractions,
                fallback_errors=fallback_errors,
            )
        )
