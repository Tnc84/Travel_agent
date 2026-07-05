from __future__ import annotations

from dataclasses import dataclass

from core.graph.config import GraphRuntimeConfig, load_graph_config
from core.location import LocationResolver
from core.services.travel.cache import TTLCache
from core.services.travel.location import LocationService
from core.services.travel.poi import PoiService
from core.services.travel.weather import WeatherService
from core.tools.openmeteo_client import OpenMeteoClient
from core.tools.opentripmap_client import OpenTripMapClient
from core.tools.osm_overpass_client import OSMOverpassClient


@dataclass
class TravelServices:
    location: LocationService
    weather: WeatherService
    poi: PoiService
    config: GraphRuntimeConfig


def build_travel_services(
    config: GraphRuntimeConfig | None = None,
    location_resolver: LocationResolver | None = None,
) -> TravelServices:
    cfg = config or load_graph_config()
    resolver = location_resolver or LocationResolver()
    weather_cache = TTLCache(cfg.weather_cache_ttl_seconds)
    place_cache = TTLCache(cfg.place_cache_ttl_seconds)
    openmeteo = OpenMeteoClient()
    overpass = OSMOverpassClient()
    opentripmap = OpenTripMapClient()

    return TravelServices(
        location=LocationService(resolver),
        weather=WeatherService(openmeteo, weather_cache, cfg.tool_timeout_seconds),
        poi=PoiService(
            overpass,
            opentripmap,
            place_cache,
            cfg.tool_timeout_seconds,
            cfg.search_radius_m,
        ),
        config=cfg,
    )
