from __future__ import annotations

import concurrent.futures
import logging
from typing import Any, Dict

from core.graph.nodes.runtime import get_runtime, timed_node
from core.graph.state import NodeErrorKind, make_error
from core.location import LocationResult

logger = logging.getLogger(__name__)


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
        return {
            "errors": {
                "fetch_weather": make_error(
                    "fetch_weather", NodeErrorKind.NON_RETRYABLE,
                    "missing resolved_location or date_str",
                )
            }
        }

    location = LocationResult.from_dict(resolved)
    cache_key = f"{location.lat:.4f}:{location.lon:.4f}:{date_str}"
    cached = runtime.weather_cache.get(cache_key)
    if cached:
        return {"weather": cached}

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                runtime.openmeteo.get_daily_forecast,
                location.lat,
                location.lon,
                date_str,
            )
            payload = future.result(timeout=runtime.config.tool_timeout_seconds)
    except concurrent.futures.TimeoutError:
        logger.warning("fetch_weather timeout after %.1fs", runtime.config.tool_timeout_seconds)
        return {
            "errors": {
                "fetch_weather": make_error(
                    "fetch_weather", NodeErrorKind.TIMEOUT, "timed out",
                    provider="open_meteo",
                )
            }
        }
    except Exception as exc:
        logger.warning("fetch_weather failed: %s", exc)
        return {
            "errors": {
                "fetch_weather": make_error(
                    "fetch_weather", NodeErrorKind.PROVIDER_UNAVAILABLE,
                    f"{type(exc).__name__}: {exc}", provider="open_meteo",
                )
            }
        }

    runtime.weather_cache.set(cache_key, payload)
    return {"weather": payload}
