import json
import logging
import time
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class LocationCache:
    def __init__(self, ttl_seconds: int = 3600, persistence_path: Optional[str] = None):
        self.ttl_seconds = ttl_seconds
        self._entries: Dict[str, Tuple[float, Dict]] = {}
        self.persistence_path = Path(persistence_path) if persistence_path else None
        if self.persistence_path:
            self._load_from_disk()

    def get(self, key: str) -> Optional[Dict]:
        entry = self._entries.get(key)
        if not entry:
            return None

        expires_at, value = entry
        if expires_at < time.time():
            self._entries.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Dict) -> None:
        expires_at = time.time() + self.ttl_seconds
        self._entries[key] = (expires_at, value)
        if self.persistence_path:
            self._save_to_disk()

    def _load_from_disk(self) -> None:
        if not self.persistence_path or not self.persistence_path.exists():
            return

        try:
            payload = json.loads(self.persistence_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Could not load location cache file: %s", exc)
            return

        now = time.time()
        for item in payload.get("entries", []):
            key = item.get("key")
            expires_at = float(item.get("expires_at", 0))
            value = item.get("value")
            if key and value and expires_at > now:
                self._entries[key] = (expires_at, value)

    def _save_to_disk(self) -> None:
        if not self.persistence_path:
            return

        self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "entries": [
                {"key": key, "expires_at": expires_at, "value": value}
                for key, (expires_at, value) in self._entries.items()
            ]
        }
        try:
            self.persistence_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("Could not persist location cache file: %s", exc)
