from __future__ import annotations

from dotenv import load_dotenv

from core.services.travel import TravelServices, build_travel_services

_services: TravelServices | None = None


def get_services() -> TravelServices:
    global _services
    if _services is None:
        load_dotenv()
        _services = build_travel_services()
    return _services
