import os
from datetime import date, timedelta
from typing import Dict

import requests


_FORECAST_HORIZON_DAYS = 14


class OpenMeteoClient:
    _user_agent = "travel-agent-pipeline/1.0 (contact: travel-agent@example.com)"

    def __init__(
        self,
        forecast_endpoint: str | None = None,
        archive_endpoint: str | None = None,
        timeout_seconds: float | None = None,
    ):
        self.forecast_endpoint = forecast_endpoint or os.getenv(
            "OPEN_METEO_ENDPOINT", "https://api.open-meteo.com/v1/forecast"
        )
        self.archive_endpoint = archive_endpoint or os.getenv(
            "OPEN_METEO_ARCHIVE_ENDPOINT", "https://archive-api.open-meteo.com/v1/archive"
        )
        self.timeout_seconds = timeout_seconds or float(os.getenv("OPEN_METEO_TIMEOUT_SECONDS", "6"))

    def get_daily_forecast(self, lat: float, lon: float, date_str: str) -> Dict:
        if self._is_within_forecast_horizon(date_str):
            return self._fetch_forecast(lat, lon, date_str)
        return self._fetch_climate_normal(lat, lon, date_str)

    def _fetch_forecast(self, lat: float, lon: float, date_str: str) -> Dict:
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode",
            "timezone": "auto",
            "start_date": date_str,
            "end_date": date_str,
        }
        response = requests.get(
            self.forecast_endpoint,
            params=params,
            timeout=self.timeout_seconds,
            headers={"User-Agent": self._user_agent},
        )
        response.raise_for_status()
        daily = response.json().get("daily", {})
        return {
            "date": date_str,
            "tmax_c": self._first(daily.get("temperature_2m_max")),
            "tmin_c": self._first(daily.get("temperature_2m_min")),
            "precipitation_probability_max": self._first(daily.get("precipitation_probability_max")),
            "weather_code": self._first(daily.get("weathercode")),
            "source": "open_meteo_forecast",
        }

    def _fetch_climate_normal(self, lat: float, lon: float, date_str: str) -> Dict:
        target = date.fromisoformat(date_str)
        last_full_year = date.today().year - 1
        start = date(last_full_year, target.month, min(target.day, 28))
        end = start
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
            "timezone": "auto",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        }
        response = requests.get(
            self.archive_endpoint,
            params=params,
            timeout=self.timeout_seconds,
            headers={"User-Agent": self._user_agent},
        )
        response.raise_for_status()
        daily = response.json().get("daily", {})
        return {
            "date": date_str,
            "tmax_c": self._first(daily.get("temperature_2m_max")),
            "tmin_c": self._first(daily.get("temperature_2m_min")),
            "precipitation_sum_mm": self._first(daily.get("precipitation_sum")),
            "weather_code": self._first(daily.get("weathercode")),
            "source": "open_meteo_climate_normal",
            "note": (
                f"Beyond live forecast horizon. Showing climate normal from {start.isoformat()} "
                "(historical reference, same day-of-year)."
            ),
        }

    def _is_within_forecast_horizon(self, date_str: str) -> bool:
        try:
            target = date.fromisoformat(date_str)
        except ValueError:
            return True
        return target <= date.today() + timedelta(days=_FORECAST_HORIZON_DAYS)

    @staticmethod
    def _first(values):
        if not values:
            return None
        return values[0]
