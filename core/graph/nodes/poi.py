from __future__ import annotations

from typing import Any, Dict

from core.graph.nodes.runtime import get_runtime, timed_node
from core.location import LocationResult
from core.services.travel import service_error_to_node_error


@timed_node("fetch_poi")
def fetch_poi_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch combined OSM POIs with OpenTripMap fallback for attractions.

    Reads:  resolved_location
    Writes: hotels, restaurants, attractions, errors
    """
    runtime = get_runtime()
    resolved = state.get("resolved_location") or {}
    if not resolved:
        from core.graph.state import NodeErrorKind, make_error

        return {
            "errors": {
                "fetch_poi": make_error(
                    "fetch_poi", NodeErrorKind.NON_RETRYABLE,
                    "missing resolved_location",
                )
            }
        }

    location = LocationResult.from_dict(resolved)
    result = runtime.services.poi.fetch(location.lat, location.lon)
    if not result.ok:
        return {"errors": {"fetch_poi": service_error_to_node_error("fetch_poi", result.error)}}

    poi = result.data
    patch: Dict[str, Any] = {
        "hotels": poi.hotels,
        "restaurants": poi.restaurants,
        "attractions": poi.attractions,
    }
    if poi.fallback_errors:
        patch["errors"] = {
            key: service_error_to_node_error(key, err)
            for key, err in poi.fallback_errors.items()
        }
    return patch
