from __future__ import annotations

import time
from typing import Any, Dict


class TTLCache:
    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds
        self._store: Dict[str, tuple[float, Any]] = {}

    def get(self, key: str):
        value = self._store.get(key)
        if not value:
            return None
        expires_at, payload = value
        if time.time() > expires_at:
            self._store.pop(key, None)
            return None
        return payload

    def set(self, key: str, payload: Any) -> None:
        self._store[key] = (time.time() + self.ttl_seconds, payload)
