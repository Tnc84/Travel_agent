from __future__ import annotations

import concurrent.futures
import logging
from typing import Any, Dict, List

from core.graph.nodes.runtime import get_runtime, timed_node
from core.graph.state import NodeErrorKind, make_error
from core.location import LocationResult

logger = logging.getLogger(__name__)

_CATEGORIES = ("hotels", "restaurants", "attractions")


@timed_node("fetch_poi")
def fetch_poi_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch combined OSM POIs with OpenTripMap fallback for attractions.

    Reads:  resolved_location
    Writes: hotels, restaurants, attractions, errors
    """
    runtime = get_runtime()
    resolved = state.get("resolved_location") or {}
    if not resolved:
        return {
            "errors": {
                "fetch_poi": make_error(
                    "fetch_poi", NodeErrorKind.NON_RETRYABLE,
                    "missing resolved_location",
                )
            }
        }

    location = LocationResult.from_dict(resolved)
    radius_m = runtime.config.search_radius_m
    cache_key = f"osm_combined:{location.lat:.4f}:{location.lon:.4f}:{radius_m}"

    grouped = runtime.place_cache.get(cache_key)
    errors: Dict[str, Any] = {}

    if grouped is None:
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    runtime.overpass.search_combined,
                    location.lat,
                    location.lon,
                    radius_m,
                    _CATEGORIES,
                    12,
                )
                grouped = future.result(timeout=runtime.config.tool_timeout_seconds)
            runtime.place_cache.set(cache_key, grouped)
        except concurrent.futures.TimeoutError:
            logger.warning("fetch_poi overpass timeout")
            return {
                "errors": {
                    "fetch_poi": make_error(
                        "fetch_poi", NodeErrorKind.TIMEOUT,
                        "overpass timed out", provider="osm_overpass",
                    )
                }
            }
        except Exception as exc:
            logger.warning("fetch_poi overpass failed: %s", exc)
            return {
                "errors": {
                    "fetch_poi": make_error(
                        "fetch_poi", NodeErrorKind.PROVIDER_UNAVAILABLE,
                        f"{type(exc).__name__}: {exc}", provider="osm_overpass",
                    )
                }
            }

    hotels: List[Dict] = list(grouped.get("hotels", []))
    restaurants: List[Dict] = list(grouped.get("restaurants", []))
    attractions: List[Dict] = list(grouped.get("attractions", []))

    if len(attractions) < 3 and runtime.opentripmap.is_enabled():
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    runtime.opentripmap.find_attractions,
                    location.lat,
                    location.lon,
                    radius_m,
                    8,
                )
                fallback = future.result(timeout=runtime.config.tool_timeout_seconds)
            attractions.extend(fallback)
        except Exception as exc:
            logger.warning("OpenTripMap fallback failed: %s", exc)
            errors["fetch_poi_fallback"] = make_error(
                "fetch_poi_fallback", NodeErrorKind.PROVIDER_UNAVAILABLE,
                f"{type(exc).__name__}: {exc}", provider="open_trip_map",
            )

    patch: Dict[str, Any] = {
        "hotels": hotels,
        "restaurants": restaurants,
        "attractions": attractions,
    }
    if errors:
        patch["errors"] = errors
    return patch
