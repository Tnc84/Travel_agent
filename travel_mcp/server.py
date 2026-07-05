"""MCP server entrypoint for the Travel Agent."""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from travel_mcp.schemas import (
    FavoriteOutput,
    GetTripOutput,
    GetWeatherOutput,
    ListTripsOutput,
    ResolveLocationOutput,
    SaveTripOutput,
    SearchPoiOutput,
)
from travel_mcp.wiring import get_services

mcp = FastMCP("travel-agent")


@mcp.tool()
def resolve_location(query: str, country_hint: str | None = None) -> dict[str, Any]:
    """Resolve a place name to coordinates and canonical location."""
    result = get_services().location.resolve(query, country_hint)
    data = result.data
    output = ResolveLocationOutput(
        ok=not data.needs_clarification or data.resolved is not None,
        resolved=data.resolved.to_dict() if data.resolved else None,
        clarification=data.clarification,
        needs_clarification=data.needs_clarification,
    )
    return output.model_dump()


@mcp.tool()
def get_weather(lat: float, lon: float, date_str: str) -> dict[str, Any]:
    """Fetch daily weather forecast or climate normal for a date."""
    result = get_services().weather.fetch(lat, lon, date_str)
    if result.ok:
        return GetWeatherOutput(ok=True, weather=result.data).model_dump()
    return GetWeatherOutput(ok=False, error=result.error.message).model_dump()


@mcp.tool()
def search_poi(lat: float, lon: float, radius_m: int | None = None) -> dict[str, Any]:
    """Search hotels, restaurants, and attractions near coordinates."""
    result = get_services().poi.fetch(lat, lon, radius_m)
    if not result.ok:
        return SearchPoiOutput(ok=False, error=result.error.message).model_dump()
    poi = result.data
    return SearchPoiOutput(
        ok=True,
        hotels=poi.hotels,
        restaurants=poi.restaurants,
        attractions=poi.attractions,
    ).model_dump()


def _trip_service():
    from core.persistence.repositories.trips import TripRepository

    return TripRepository()


@mcp.tool()
def save_trip(
    user_id: str,
    query: str,
    location: str,
    date_str: str,
    response: str,
    resolved_location: dict[str, Any] | None = None,
    graph_run_id: str | None = None,
    thread_id: str | None = None,
) -> dict[str, Any]:
    """Save a completed travel guide for a user."""
    try:
        trip_id = _trip_service().save_trip(
            user_id=user_id,
            query=query,
            location=location,
            date_str=date_str,
            response=response,
            resolved_location=resolved_location,
            graph_run_id=graph_run_id,
            thread_id=thread_id,
        )
        return SaveTripOutput(ok=True, trip_id=trip_id).model_dump()
    except Exception as exc:
        return SaveTripOutput(ok=False, error=str(exc)).model_dump()


@mcp.tool()
def list_user_trips(user_id: str, limit: int = 20) -> dict[str, Any]:
    """List saved trips for a user."""
    try:
        trips = _trip_service().list_by_user(user_id, limit=limit)
        return ListTripsOutput(ok=True, trips=trips).model_dump()
    except Exception as exc:
        return ListTripsOutput(ok=False, error=str(exc)).model_dump()


@mcp.tool()
def get_trip(trip_id: str) -> dict[str, Any]:
    """Get full details of a saved trip."""
    try:
        trip = _trip_service().get_by_id(trip_id)
        if trip is None:
            return GetTripOutput(ok=False, error="trip not found").model_dump()
        return GetTripOutput(ok=True, trip=trip).model_dump()
    except Exception as exc:
        return GetTripOutput(ok=False, error=str(exc)).model_dump()


@mcp.tool()
def add_trip_favorite(user_id: str, trip_id: str) -> dict[str, Any]:
    """Mark a trip as favorite for a user."""
    try:
        _trip_service().add_favorite(user_id, trip_id)
        return FavoriteOutput(ok=True).model_dump()
    except Exception as exc:
        return FavoriteOutput(ok=False, error=str(exc)).model_dump()


@mcp.tool()
def remove_trip_favorite(user_id: str, trip_id: str) -> dict[str, Any]:
    """Remove a trip from user favorites."""
    try:
        _trip_service().remove_favorite(user_id, trip_id)
        return FavoriteOutput(ok=True).model_dump()
    except Exception as exc:
        return FavoriteOutput(ok=False, error=str(exc)).model_dump()


@mcp.resource("travel://trips/{user_id}")
def trips_resource(user_id: str) -> str:
    """Recent saved trips for a user (read-only JSON)."""
    try:
        trips = _trip_service().list_by_user(user_id, limit=20)
        return json.dumps([t.model_dump() for t in trips], indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.resource("travel://trip/{trip_id}")
def trip_resource(trip_id: str) -> str:
    """Full saved trip details (read-only JSON)."""
    try:
        trip = _trip_service().get_by_id(trip_id)
        if trip is None:
            return json.dumps({"error": "trip not found"})
        return json.dumps(trip, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
