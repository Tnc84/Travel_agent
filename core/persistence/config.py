from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PersistenceConfig:
    database_dsn: Optional[str]

    @property
    def enabled(self) -> bool:
        return bool(self.database_dsn)


def load_persistence_config() -> PersistenceConfig:
    dsn = (os.getenv("APP_DATABASE_DSN") or "").strip() or None
    return PersistenceConfig(database_dsn=dsn)
