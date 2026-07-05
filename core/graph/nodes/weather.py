from __future__ import annotations

from typing import Any, Dict

from core.graph.nodes.runtime import get_runtime, timed_node
from core.location import LocationResult
from core.services.travel import service_error_to_node_error


@timed_node("fetch_weather")
def fetch_weather_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch daily forecast / climate-normal with timeout and TTL cache.

    Reads:  resolved_location, date_str
    Writes: weather, errors
    """
    runtime = get_runtime()
    resolved = state.get("resolved_location") or {}
    date_str = state.get("date_str") or ""
    if not resolved or not date_str:
        from core.graph.state import NodeErrorKind, make_error

        return {
            "errors": {
                "fetch_weather": make_error(
                    "fetch_weather", NodeErrorKind.NON_RETRYABLE,
                    "missing resolved_location or date_str",
                )
            }
        }

    location = LocationResult.from_dict(resolved)
    result = runtime.services.weather.fetch(location.lat, location.lon, date_str)
    if not result.ok:
        return {"errors": {"fetch_weather": service_error_to_node_error("fetch_weather", result.error)}}
    return {"weather": result.data}
