from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GraphRuntimeConfig:
    enabled: bool
    checkpoint_dsn: Optional[str]
    allow_no_checkpoint: bool
    thread_ttl_seconds: int
    tool_timeout_seconds: float
    global_timeout_seconds: float
    search_radius_m: int
    weather_cache_ttl_seconds: int
    place_cache_ttl_seconds: int

    @property
    def has_checkpoint(self) -> bool:
        return bool(self.checkpoint_dsn)


class GraphConfigError(RuntimeError):
    """Raised at startup when the LangGraph runtime config is invalid."""


def _bool_env(key: str, default: str) -> bool:
    return os.getenv(key, default).strip().lower() in {"1", "true", "yes", "on"}


def load_graph_config() -> GraphRuntimeConfig:
    """Load graph runtime config from the environment.

    If ``LANGGRAPH_CHECKPOINT_DSN`` is unset and ``LANGGRAPH_ALLOW_NO_CHECKPOINT`` is not
    set, the runtime defaults to **in-memory** checkpointing so local runs (``run.py``)
    work without Postgres. Set ``LANGGRAPH_ALLOW_NO_CHECKPOINT=0`` to require a DSN.
    """
    dsn_raw = os.getenv("LANGGRAPH_CHECKPOINT_DSN")
    checkpoint_dsn = (dsn_raw or "").strip() or None
    allow_raw = os.getenv("LANGGRAPH_ALLOW_NO_CHECKPOINT")
    if checkpoint_dsn:
        allow_no_checkpoint = (
            _bool_env("LANGGRAPH_ALLOW_NO_CHECKPOINT", "0") if allow_raw is not None else False
        )
    else:
        if allow_raw is not None:
            allow_no_checkpoint = _bool_env("LANGGRAPH_ALLOW_NO_CHECKPOINT", "1")
        else:
            allow_no_checkpoint = True
            logger.warning(
                "LANGGRAPH_CHECKPOINT_DSN unset; using in-memory LangGraph checkpoint "
                "(no durability). Set LANGGRAPH_CHECKPOINT_DSN or LANGGRAPH_ALLOW_NO_CHECKPOINT=0 "
                "for Postgres-only startup."
            )

    return GraphRuntimeConfig(
        enabled=_bool_env("LANGGRAPH_ENABLED", "1"),
        checkpoint_dsn=checkpoint_dsn,
        allow_no_checkpoint=allow_no_checkpoint,
        thread_ttl_seconds=int(os.getenv("LANGGRAPH_THREAD_TTL_SECONDS", "86400")),
        tool_timeout_seconds=float(os.getenv("TRAVEL_TOOL_TIMEOUT_SECONDS", "8")),
        global_timeout_seconds=float(os.getenv("TRAVEL_GLOBAL_TIMEOUT_SECONDS", "90")),
        search_radius_m=int(os.getenv("TRAVEL_SEARCH_RADIUS_M", "4000")),
        weather_cache_ttl_seconds=int(os.getenv("TRAVEL_WEATHER_CACHE_TTL_SECONDS", "1800")),
        place_cache_ttl_seconds=int(os.getenv("TRAVEL_PLACES_CACHE_TTL_SECONDS", "1800")),
    )


def validate_graph_config(config: GraphRuntimeConfig) -> None:
    if not config.enabled:
        raise GraphConfigError(
            "LANGGRAPH_ENABLED must be truthy in this build (legacy pipeline removed)."
        )
    if not config.checkpoint_dsn and not config.allow_no_checkpoint:
        raise GraphConfigError(
            "LANGGRAPH_CHECKPOINT_DSN is required when LANGGRAPH_ALLOW_NO_CHECKPOINT=0 "
            "(unset LANGGRAPH_ALLOW_NO_CHECKPOINT defaults to in-memory checkpointing)."
        )
    if config.tool_timeout_seconds <= 0 or config.global_timeout_seconds <= 0:
        raise GraphConfigError("Tool/global timeouts must be positive numbers.")
    if config.global_timeout_seconds < config.tool_timeout_seconds:
        raise GraphConfigError(
            "TRAVEL_GLOBAL_TIMEOUT_SECONDS must be >= TRAVEL_TOOL_TIMEOUT_SECONDS."
        )
