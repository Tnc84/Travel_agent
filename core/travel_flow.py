import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional

from core.base import Message
from core.coordinator import Coordinator
from core.location_resolver import LocationResolver, LocationResult
from core.travel_pipeline import SectionResults, TravelContext, TravelPipeline


@dataclass(frozen=True)
class LocationResolution:
    resolved_location: Optional[LocationResult]
    clarification_message: Optional[str]


def resolve_location_for_travel(
    location: str,
    location_resolver: LocationResolver,
) -> LocationResolution:
    resolved_location = location_resolver.resolve(location)
    if not location_resolver.is_confident(resolved_location):
        return LocationResolution(
            resolved_location=resolved_location,
            clarification_message=(
                f"I found multiple possible matches for '{location}'. "
                "Please include country or county to continue."
            ),
        )
    return LocationResolution(resolved_location=resolved_location, clarification_message=None)


def build_single_call_travel_prompt(canonical_location: str, date_str: str) -> str:
    return (
        f"Create a concise travel recommendation for {canonical_location} on {date_str}.\n"
        "Do not add a title. Do not add an introduction or conclusion. Do not use numbered section headers.\n"
        "Return short, practical bullet points only, in this order:\n"
        "- Weather (1-2 bullets)\n"
        "- Hotels (top 3)\n"
        "- Restaurants (top 3)\n"
        "- Attractions (top 3)\n"
        "If real-time data is unavailable, state that briefly and provide best-effort guidance."
    )


def build_tool_context_prompt(canonical_location: str, date_str: str, sections: SectionResults) -> str:
    weather = sections.weather or {}
    hotels = _format_places("Hotels", sections.hotels)
    restaurants = _format_places("Restaurants", sections.restaurants)
    attractions = _format_places("Attractions", sections.attractions)
    return (
        f"Create a concise travel recommendation for {canonical_location} on {date_str}.\n"
        "Use only the tool data below. Do not invent phone numbers.\n"
        "Do not add title/introduction/conclusion. Return practical bullets grouped as Weather, Hotels, Restaurants, Attractions.\n\n"
        f"Weather data: {weather}\n\n"
        f"{hotels}\n\n"
        f"{restaurants}\n\n"
        f"{attractions}\n"
    )


def generate_travel_response(
    coordinator: Coordinator,
    canonical_location: str,
    date_str: str,
) -> Message:
    guide_prompt = build_single_call_travel_prompt(canonical_location, date_str)
    return coordinator.process_message(Message(content=guide_prompt, sender="User"), "Assistant")


def run_travel_pipeline(
    resolved_location: LocationResult,
    date_str: str,
    event_callback=None,
) -> SectionResults:
    pipeline = TravelPipeline()
    context = TravelContext(location=resolved_location, date_str=date_str)
    return asyncio.run(pipeline.run(context, on_event=event_callback))


def generate_travel_response_with_tools(
    coordinator: Coordinator,
    canonical_location: str,
    date_str: str,
    sections: SectionResults,
) -> Message:
    prompt = build_tool_context_prompt(canonical_location, date_str, sections)
    return coordinator.process_message(Message(content=prompt, sender="User"), "Assistant")


def build_structured_fallback_response(canonical_location: str, date_str: str, sections: SectionResults) -> str:
    weather_text = _format_weather_line(sections, date_str)
    osm_error = _osm_error_message(sections.errors)

    lines = [
        f"Travel guide for {canonical_location} ({date_str})",
        "Weather:",
        weather_text,
        "Hotels:",
        *_format_place_lines(sections.hotels, osm_error),
        "Restaurants:",
        *_format_place_lines(sections.restaurants, osm_error),
        "Attractions:",
        *_format_place_lines(sections.attractions, osm_error),
    ]
    if osm_error:
        lines.append("")
        lines.append(f"Note: {osm_error}")
    return "\n".join(lines)


def _format_weather_line(sections: SectionResults, date_str: str) -> str:
    weather = sections.weather
    if not weather:
        weather_error = sections.errors.get("weather_ready")
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


def _osm_error_message(errors: Dict[str, str]) -> Optional[str]:
    relevant = [errors[key] for key in ("hotels_ready", "restaurants_ready", "attractions_ready") if key in errors]
    if not relevant:
        return None
    return "Points-of-interest data temporarily unavailable (OSM Overpass not responding). Please retry shortly."


def _format_places(title: str, places: List[Dict]) -> str:
    lines = _format_place_lines(places)
    return f"{title}:\n" + "\n".join(lines)


def _format_place_lines(places: List[Dict], unavailable_message: Optional[str] = None) -> List[str]:
    if not places:
        return [f"- {unavailable_message}" if unavailable_message else "- No data available."]
    lines = []
    for item in places[:5]:
        phone = item.get("phone") if item.get("phone") else "unavailable"
        distance = item.get("distance_m")
        distance_label = f"{int(distance)}m" if isinstance(distance, (int, float)) else "unknown distance"
        lines.append(f"- {item.get('name', 'Unknown')} | phone: {phone} | distance: {distance_label}")
    return lines
