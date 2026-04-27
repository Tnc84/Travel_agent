import os
from typing import Dict

import requests


class OpenMeteoClient:
    def __init__(self, endpoint: str | None = None, timeout_seconds: float | None = None):
        self.endpoint = endpoint or os.getenv("OPEN_METEO_ENDPOINT", "https://api.open-meteo.com/v1/forecast")
        self.timeout_seconds = timeout_seconds or float(os.getenv("OPEN_METEO_TIMEOUT_SECONDS", "6"))

    def get_daily_forecast(self, lat: float, lon: float, date_str: str) -> Dict:
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode",
            "timezone": "auto",
            "start_date": date_str,
            "end_date": date_str,
        }
        response = requests.get(self.endpoint, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        data = response.json()
        daily = data.get("daily", {})
        return {
            "date": date_str,
            "tmax_c": self._first(daily.get("temperature_2m_max")),
            "tmin_c": self._first(daily.get("temperature_2m_min")),
            "precipitation_probability_max": self._first(daily.get("precipitation_probability_max")),
            "weather_code": self._first(daily.get("weathercode")),
            "source": "open_meteo",
        }

    @staticmethod
    def _first(values):
        if not values:
            return None
        return values[0]
