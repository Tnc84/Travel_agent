import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

from core.support import retry_on_error

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT_SECONDS = 8


@dataclass(frozen=True)
class LocationCandidate:
    query: str
    canonical_name: str
    lat: float
    lon: float
    country_code: str
    place_type: str
    importance: float
    provider: str


class BaseLocationProvider:
    name = "base"

    def search(self, query: str, country_code: Optional[str] = None) -> List[LocationCandidate]:
        raise NotImplementedError


class NominatimLocationProvider(BaseLocationProvider):
    name = "nominatim"
    _endpoint = "https://nominatim.openstreetmap.org/search"
    _user_agent = "travel-agent-location-resolver/1.0"

    @retry_on_error(max_retries=2, delay=0.5, exceptions=(requests.ConnectionError, requests.Timeout))
    def _get(self, params: Dict[str, Any]) -> requests.Response:
        return requests.get(
            self._endpoint,
            params=params,
            timeout=_DEFAULT_TIMEOUT_SECONDS,
            headers={"User-Agent": self._user_agent},
        )

    def search(self, query: str, country_code: Optional[str] = None) -> List[LocationCandidate]:
        params: Dict[str, Any] = {
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": 5,
        }
        if country_code:
            params["countrycodes"] = country_code.lower()

        try:
            response = self._get(params)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            logger.warning("Nominatim search failed for '%s': %s", query, exc)
            return []

        candidates: List[LocationCandidate] = []
        for item in payload:
            try:
                candidates.append(
                    LocationCandidate(
                        query=query,
                        canonical_name=item.get("display_name", "").strip(),
                        lat=float(item.get("lat")),
                        lon=float(item.get("lon")),
                        country_code=(item.get("address", {}).get("country_code", "") or "").lower(),
                        place_type=(item.get("type", "") or item.get("category", "unknown")).lower(),
                        importance=float(item.get("importance", 0.0) or 0.0),
                        provider=self.name,
                    )
                )
            except (TypeError, ValueError):
                continue

        return candidates


class PhotonLocationProvider(BaseLocationProvider):
    name = "photon"
    _endpoint = "https://photon.komoot.io/api/"

    @retry_on_error(max_retries=2, delay=0.5, exceptions=(requests.ConnectionError, requests.Timeout))
    def _get(self, params: Dict[str, Any]) -> requests.Response:
        return requests.get(self._endpoint, params=params, timeout=_DEFAULT_TIMEOUT_SECONDS)

    def search(self, query: str, country_code: Optional[str] = None) -> List[LocationCandidate]:
        params: Dict[str, Any] = {"q": query, "limit": 5}
        if country_code:
            params["lang"] = "en"

        try:
            response = self._get(params)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            logger.warning("Photon search failed for '%s': %s", query, exc)
            return []

        candidates: List[LocationCandidate] = []
        for feature in payload.get("features", []):
            geometry = feature.get("geometry", {})
            properties = feature.get("properties", {})
            coords = geometry.get("coordinates", [])
            if len(coords) != 2:
                continue

            candidate_country_code = (properties.get("countrycode", "") or "").lower()
            if country_code and candidate_country_code and candidate_country_code != country_code.lower():
                continue

            name = properties.get("name") or ""
            state = properties.get("state") or properties.get("county") or ""
            country = properties.get("country") or ""
            label_parts = [part for part in (name, state, country) if part]

            try:
                candidates.append(
                    LocationCandidate(
                        query=query,
                        canonical_name=", ".join(label_parts).strip(),
                        lat=float(coords[1]),
                        lon=float(coords[0]),
                        country_code=candidate_country_code,
                        place_type=(properties.get("osm_value", "") or properties.get("type", "unknown")).lower(),
                        importance=float(properties.get("importance", 0.0) or 0.0),
                        provider=self.name,
                    )
                )
            except (TypeError, ValueError):
                continue

        return candidates
