from __future__ import annotations

import concurrent.futures
import logging
from typing import Any, Dict

from core.services.travel.cache import TTLCache
from core.services.travel.results import ServiceError, ServiceErrorKind, ServiceResult
from core.tools.openmeteo_client import OpenMeteoClient

logger = logging.getLogger(__name__)


class WeatherService:
    def __init__(
        self,
        client: OpenMeteoClient,
        cache: TTLCache,
        timeout_seconds: float,
    ):
        self._client = client
        self._cache = cache
        self._timeout_seconds = timeout_seconds

    def fetch(self, lat: float, lon: float, date_str: str) -> ServiceResult[Dict[str, Any]]:
        if not date_str:
            return ServiceResult.failure(
                ServiceError(
                    ServiceErrorKind.NON_RETRYABLE,
                    "missing date_str",
                )
            )

        cache_key = f"{lat:.4f}:{lon:.4f}:{date_str}"
        cached = self._cache.get(cache_key)
        if cached:
            return ServiceResult.success(cached)

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(self._client.get_daily_forecast, lat, lon, date_str)
                payload = future.result(timeout=self._timeout_seconds)
        except concurrent.futures.TimeoutError:
            logger.warning("WeatherService timeout after %.1fs", self._timeout_seconds)
            return ServiceResult.failure(
                ServiceError(ServiceErrorKind.TIMEOUT, "timed out", provider="open_meteo")
            )
        except Exception as exc:
            logger.warning("WeatherService failed: %s", exc)
            return ServiceResult.failure(
                ServiceError(
                    ServiceErrorKind.PROVIDER_UNAVAILABLE,
                    f"{type(exc).__name__}: {exc}",
                    provider="open_meteo",
                )
            )

        self._cache.set(cache_key, payload)
        return ServiceResult.success(payload)
