"""Geocoding subsystem: free-tier resolver, providers and TTL cache.

Public API:
    - LocationResolver: canonical destination resolution + clarification semantics.
    - LocationResult:   typed value object for a resolved destination.

Internal modules (`cache`, `providers`) are not part of the public surface and
should not be imported directly from outside this package.
"""
from core.location.resolver import LocationResolver, LocationResult

__all__ = ["LocationResolver", "LocationResult"]
