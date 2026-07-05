from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from core.persistence.config import PersistenceConfig, load_persistence_config

logger = logging.getLogger(__name__)

_pool: Optional[ConnectionPool] = None


def get_pool(config: PersistenceConfig | None = None) -> ConnectionPool:
    global _pool
    cfg = config or load_persistence_config()
    if not cfg.enabled:
        raise RuntimeError("APP_DATABASE_DSN is not configured")
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=cfg.database_dsn,
            kwargs={"row_factory": dict_row},
            min_size=1,
            max_size=5,
        )
        logger.info("Postgres app database pool ready")
    return _pool


@contextmanager
def db_connection(config: PersistenceConfig | None = None) -> Iterator[psycopg.Connection]:
    pool = get_pool(config)
    with pool.connection() as conn:
        yield conn


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def run_migrations(config: PersistenceConfig | None = None) -> None:
    cfg = config or load_persistence_config()
    if not cfg.enabled:
        return
    migration_path = Path(__file__).parent / "migrations" / "001_initial.sql"
    with migration_path.open(encoding="utf-8") as handle:
        sql = handle.read()
    with db_connection(cfg) as conn:
        conn.execute(sql)
        conn.commit()
    logger.info("App database migrations applied")
