from __future__ import annotations

from typing import Optional

from core.location import LocationResolver
from core.services.travel.results import ResolveLocationData, ServiceResult


class LocationService:
    def __init__(self, resolver: LocationResolver):
        self._resolver = resolver

    def resolve(
        self, query: str, country_hint: Optional[str] = None
    ) -> ServiceResult[ResolveLocationData]:
        raw = (query or "").strip()
        if not raw:
            return ServiceResult.success(
                ResolveLocationData(
                    resolved=None,
                    clarification="Please provide a destination.",
                    needs_clarification=True,
                )
            )

        resolved = self._resolver.resolve(raw, country_hint)
        clarification = self._resolver.clarification_message(raw, resolved)
        return ServiceResult.success(
            ResolveLocationData(
                resolved=resolved,
                clarification=clarification,
                needs_clarification=clarification is not None,
            )
        )
