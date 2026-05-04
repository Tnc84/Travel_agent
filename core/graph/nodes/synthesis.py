from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.agent_platform import Message
from core.graph.nodes.runtime import get_runtime, timed_node
from core.graph.state import GraphStatus, NodeErrorKind, make_error
from core.support import clean_llm_response

logger = logging.getLogger(__name__)


@dataclass
class _SectionView:
    weather: Optional[Dict[str, Any]]
    hotels: List[Dict[str, Any]]
    restaurants: List[Dict[str, Any]]
    attractions: List[Dict[str, Any]]
    errors: Dict[str, str]


def _section_view(state: Dict[str, Any]) -> _SectionView:
    return _SectionView(
        weather=state.get("weather"),
        hotels=list(state.get("hotels") or []),
        restaurants=list(state.get("restaurants") or []),
        attractions=list(state.get("attractions") or []),
        errors={k: v.get("message", "") for k, v in (state.get("errors") or {}).items()},
    )


def _format_place_lines(places: List[Dict], unavailable_message: Optional[str] = None) -> List[str]:
    if not places:
        return [f"- {unavailable_message}" if unavailable_message else "- No data available."]
    lines: List[str] = []
    for item in places[:5]:
        phone = item.get("phone") if item.get("phone") else "unavailable"
        distance = item.get("distance_m")
        distance_label = (
            f"{int(distance)}m" if isinstance(distance, (int, float)) else "unknown distance"
        )
        lines.append(
            f"- {item.get('name', 'Unknown')} | phone: {phone} | distance: {distance_label}"
        )
    return lines


def _format_places_block(title: str, places: List[Dict]) -> str:
    return f"{title}:\n" + "\n".join(_format_place_lines(places))


def _osm_unavailable_message(errors: Dict[str, str]) -> Optional[str]:
    keys = ("fetch_poi", "fetch_poi_fallback", "hotels_ready", "restaurants_ready", "attractions_ready")
    if not any(k in errors for k in keys):
        return None
    return (
        "Points-of-interest data temporarily unavailable (OSM Overpass not responding). "
        "Please retry shortly."
    )


def _format_weather_line(view: _SectionView, date_str: str) -> str:
    weather = view.weather
    if not weather:
        weather_error = view.errors.get("fetch_weather") or view.errors.get("weather_ready")
        if weather_error:
            return f"- Weather data unavailable ({weather_error})."
        return "- Weather data unavailable."
    tmin = weather.get("tmin_c", "N/A")
    tmax = weather.get("tmax_c", "N/A")
    base = f"- {weather.get('date', date_str)}: {tmin} to {tmax} C"
    if weather.get("precipitation_probability_max") is not None:
        base += f", precipitation risk {weather['precipitation_probability_max']}%."
    elif weather.get("precipitation_sum_mm") is not None:
        base += f", historical precipitation {weather['precipitation_sum_mm']}mm."
    else:
        base += "."
    if weather.get("note"):
        base += f"\n  ({weather['note']})"
    return base


def _build_tool_context_prompt(canonical_location: str, date_str: str, view: _SectionView) -> str:
    return (
        f"Create a concise travel recommendation for {canonical_location} on {date_str}.\n"
        "Use only the tool data below. Do not invent phone numbers.\n"
        "Do not add title/introduction/conclusion. Return practical bullets grouped as "
        "Weather, Hotels, Restaurants, Attractions.\n\n"
        f"Weather data: {view.weather or {}}\n\n"
        f"{_format_places_block('Hotels', view.hotels)}\n\n"
        f"{_format_places_block('Restaurants', view.restaurants)}\n\n"
        f"{_format_places_block('Attractions', view.attractions)}\n"
    )


def _build_structured_fallback(canonical_location: str, date_str: str, view: _SectionView) -> str:
    osm_error = _osm_unavailable_message(view.errors)
    lines = [
        f"Travel guide for {canonical_location} ({date_str})",
        "Weather:",
        _format_weather_line(view, date_str),
        "Hotels:",
        *_format_place_lines(view.hotels, osm_error),
        "Restaurants:",
        *_format_place_lines(view.restaurants, osm_error),
        "Attractions:",
        *_format_place_lines(view.attractions, osm_error),
    ]
    if osm_error:
        lines.append("")
        lines.append(f"Note: {osm_error}")
    return "\n".join(lines)


@timed_node("synthesize_response")
def synthesize_response_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LLM synthesis when at least one section has data.

    Reads:  canonical_location, date_str, weather, hotels, restaurants, attractions
    Writes: final_response, used_tool_data, status, finished_at, errors
    """
    runtime = get_runtime()
    canonical_location = state.get("canonical_location") or ""
    date_str = state.get("date_str") or ""
    view = _section_view(state)

    prompt = _build_tool_context_prompt(canonical_location, date_str, view)
    try:
        response: Message = runtime.coordinator.process_message(
            Message(content=prompt, sender="User"),
            "Assistant",
        )
        cleaned = clean_llm_response(response.content)
        return {
            "final_response": cleaned,
            "used_tool_data": True,
            "status": GraphStatus.DONE.value,
            "finished_at": time.time(),
        }
    except Exception as exc:
        logger.exception("synthesize_response failed; falling back to structured response")
        cleaned = _build_structured_fallback(canonical_location, date_str, view)
        return {
            "final_response": cleaned,
            "used_tool_data": False,
            "status": GraphStatus.DONE.value,
            "finished_at": time.time(),
            "errors": {
                "synthesize_response": make_error(
                    "synthesize_response", NodeErrorKind.PROVIDER_UNAVAILABLE,
                    f"{type(exc).__name__}: {exc}", provider="llm",
                )
            },
        }


@timed_node("fallback_response")
def fallback_response_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic structured response when no tool data is available.

    Reads:  canonical_location, date_str, weather, hotels, restaurants, attractions, errors
    Writes: final_response, used_tool_data, status, finished_at
    """
    canonical_location = state.get("canonical_location") or state.get("raw_location") or ""
    date_str = state.get("date_str") or ""
    view = _section_view(state)
    cleaned = _build_structured_fallback(canonical_location, date_str, view)
    return {
        "final_response": cleaned,
        "used_tool_data": False,
        "status": GraphStatus.DONE.value,
        "finished_at": time.time(),
    }
