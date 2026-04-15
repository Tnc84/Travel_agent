import os
import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from core.location_cache import LocationCache
from core.location_providers import (
    LocationCandidate,
    NominatimLocationProvider,
    PhotonLocationProvider,
)

_DEFAULT_CONFIDENCE_THRESHOLD = 0.55
_PLACE_TYPE_WEIGHTS: Dict[str, float] = {
    "city": 0.30,
    "town": 0.28,
    "village": 0.27,
    "municipality": 0.27,
    "resort": 0.30,
    "administrative": 0.22,
    "hamlet": 0.18,
}

_LOCAL_OVERRIDES = {
    "sovata": {
        "canonical_name": "Sovata, Mures, Romania",
        "lat": 46.5960,
        "lon": 25.0789,
        "country_code": "ro",
        "place_type": "town",
        "provider": "local_override",
    },
    "baile tusnad": {
        "canonical_name": "Baile Tusnad, Harghita, Romania",
        "lat": 46.1470,
        "lon": 25.8605,
        "country_code": "ro",
        "place_type": "town",
        "provider": "local_override",
    },
    "vatra dornei": {
        "canonical_name": "Vatra Dornei, Suceava, Romania",
        "lat": 47.3470,
        "lon": 25.3560,
        "country_code": "ro",
        "place_type": "town",
        "provider": "local_override",
    },
}
_ROMANIAN_HINTS = (
    "romania",
    "romaniai",
    "bucuresti",
    "cluj",
    "iasi",
    "timisoara",
    "constanta",
    "brasov",
    "sibiu",
    "mures",
    "harghita",
    "suceava",
    "baile",
)


@dataclass(frozen=True)
class LocationResult:
    query: str
    canonical_name: str
    lat: float
    lon: float
    country_code: str
    place_type: str
    confidence: float
    provider: str

    def to_dict(self) -> Dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> "LocationResult":
        return LocationResult(
            query=data["query"],
            canonical_name=data["canonical_name"],
            lat=float(data["lat"]),
            lon=float(data["lon"]),
            country_code=data.get("country_code", ""),
            place_type=data.get("place_type", "unknown"),
            confidence=float(data.get("confidence", 0.0)),
            provider=data.get("provider", "unknown"),
        )


class LocationResolver:
    def __init__(self):
        cache_ttl = int(os.getenv("LOCATION_CACHE_TTL_SECONDS", "21600"))
        persistence_enabled = os.getenv("LOCATION_CACHE_PERSIST", "1") == "1"
        persistence_path = "history/location_cache.json" if persistence_enabled else None
        self.cache = LocationCache(ttl_seconds=cache_ttl, persistence_path=persistence_path)
        self.providers = [NominatimLocationProvider(), PhotonLocationProvider()]
        self.confidence_threshold = float(
            os.getenv("LOCATION_CONFIDENCE_THRESHOLD", str(_DEFAULT_CONFIDENCE_THRESHOLD))
        )
        self.default_country_code = os.getenv("LOCATION_DEFAULT_COUNTRY_CODE", "ro").lower()

    def resolve(self, query: str, country_hint: Optional[str] = None) -> Optional[LocationResult]:
        normalized_query = self.normalize_query(query)
        if not normalized_query:
            return None

        cache_key = f"{normalized_query}|{(country_hint or self.default_country_code).lower()}"
        cached = self.cache.get(cache_key)
        if cached:
            return LocationResult.from_dict(cached)

        override = self._resolve_local_override(normalized_query, query)
        if override:
            self.cache.set(cache_key, override.to_dict())
            return override

        effective_country = self._resolve_country_bias(query, country_hint)
        all_candidates: List[LocationCandidate] = []
        for provider in self.providers:
            candidates = provider.search(query, effective_country)
            all_candidates.extend(candidates)
            best = self._pick_best(query, candidates, effective_country)
            if best and best.confidence >= self.confidence_threshold:
                self.cache.set(cache_key, best.to_dict())
                return best

        best_overall = self._pick_best(query, all_candidates, effective_country)
        if best_overall:
            self.cache.set(cache_key, best_overall.to_dict())
        return best_overall

    def is_confident(self, result: Optional[LocationResult]) -> bool:
        return bool(result and result.confidence >= self.confidence_threshold)

    @staticmethod
    def normalize_query(query: str) -> str:
        ascii_text = unicodedata.normalize("NFKD", query).encode("ascii", "ignore").decode("ascii")
        cleaned = re.sub(r"[^a-zA-Z0-9\s-]", " ", ascii_text.lower())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _resolve_country_bias(self, query: str, country_hint: Optional[str]) -> Optional[str]:
        if country_hint:
            return country_hint.lower()
        if self._looks_romanian_query(query):
            return self.default_country_code
        return None

    def _looks_romanian_query(self, query: str) -> bool:
        normalized = self.normalize_query(query)
        if not normalized:
            return False
        return any(hint in normalized for hint in _ROMANIAN_HINTS)

    def _resolve_local_override(self, normalized_query: str, original_query: str) -> Optional[LocationResult]:
        for key, value in _LOCAL_OVERRIDES.items():
            if key in normalized_query:
                return LocationResult(
                    query=original_query,
                    canonical_name=value["canonical_name"],
                    lat=value["lat"],
                    lon=value["lon"],
                    country_code=value["country_code"],
                    place_type=value["place_type"],
                    confidence=0.99,
                    provider=value["provider"],
                )
        return None

    def _pick_best(
        self, query: str, candidates: List[LocationCandidate], country_code: Optional[str]
    ) -> Optional[LocationResult]:
        if not candidates:
            return None

        scored = []
        for candidate in candidates:
            score = self._score_candidate(query, candidate, country_code)
            scored.append((score, candidate))

        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, best_candidate = scored[0]
        return LocationResult(
            query=query,
            canonical_name=best_candidate.canonical_name,
            lat=best_candidate.lat,
            lon=best_candidate.lon,
            country_code=best_candidate.country_code,
            place_type=best_candidate.place_type,
            confidence=max(0.0, min(1.0, best_score)),
            provider=best_candidate.provider,
        )

    def _score_candidate(
        self, query: str, candidate: LocationCandidate, country_code: Optional[str]
    ) -> float:
        normalized_query = self.normalize_query(query)
        normalized_name = self.normalize_query(candidate.canonical_name)
        query_tokens = set(normalized_query.split())
        name_tokens = set(normalized_name.split())
        overlap = len(query_tokens & name_tokens) / max(1, len(query_tokens))

        exact_bonus = 0.25 if normalized_query and normalized_query in normalized_name else 0.0
        overlap_score = overlap * 0.35
        place_weight = _PLACE_TYPE_WEIGHTS.get(candidate.place_type, 0.15)
        country_bonus = 0.10 if country_code and candidate.country_code == country_code else 0.0
        importance_bonus = min(0.20, max(0.0, candidate.importance * 0.20))
        return exact_bonus + overlap_score + place_weight + country_bonus + importance_bonus
