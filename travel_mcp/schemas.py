from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from core.persistence.schemas import TripSummary


class ResolveLocationInput(BaseModel):
    query: str = Field(description="Place name to geocode")
    country_hint: Optional[str] = Field(default=None, description="ISO country code bias, e.g. ro")


class ResolveLocationOutput(BaseModel):
    ok: bool
    resolved: Optional[Dict[str, Any]] = None
    clarification: Optional[str] = None
    needs_clarification: bool = False


class GetWeatherInput(BaseModel):
    lat: float
    lon: float
    date_str: str = Field(description="ISO date YYYY-MM-DD")


class GetWeatherOutput(BaseModel):
    ok: bool
    weather: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SearchPoiInput(BaseModel):
    lat: float
    lon: float
    radius_m: Optional[int] = Field(default=None, description="Search radius in meters")


class SearchPoiOutput(BaseModel):
    ok: bool
    hotels: list[Dict[str, Any]] = Field(default_factory=list)
    restaurants: list[Dict[str, Any]] = Field(default_factory=list)
    attractions: list[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class SaveTripInput(BaseModel):
    user_id: str
    query: str
    location: str
    date_str: str
    response: str
    resolved_location: Optional[Dict[str, Any]] = None
    graph_run_id: Optional[str] = None
    thread_id: Optional[str] = None



class SaveTripOutput(BaseModel):
    ok: bool
    trip_id: Optional[str] = None
    error: Optional[str] = None


class ListTripsOutput(BaseModel):
    ok: bool
    trips: list[TripSummary] = Field(default_factory=list)
    error: Optional[str] = None


class GetTripOutput(BaseModel):
    ok: bool
    trip: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class FavoriteOutput(BaseModel):
    ok: bool
    error: Optional[str] = None
