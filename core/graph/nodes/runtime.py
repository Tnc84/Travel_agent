from __future__ import annotations

import functools
import logging
import time
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from core.agent_platform import Coordinator
from core.graph.config import GraphRuntimeConfig
from core.location import LocationResolver
from core.tools.openmeteo_client import OpenMeteoClient
from core.tools.opentripmap_client import OpenTripMapClient
from core.tools.osm_overpass_client import OSMOverpassClient

logger = logging.getLogger(__name__)


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


@dataclass
class NodeRuntime:
    """Shared, node-visible runtime resources injected via ContextVar.

    Nodes never construct providers/clients themselves; they pull from runtime.
    """
    config: GraphRuntimeConfig
    coordinator: Coordinator
    location_resolver: LocationResolver
    overpass: OSMOverpassClient
    openmeteo: OpenMeteoClient
    opentripmap: OpenTripMapClient
    weather_cache: TTLCache
    place_cache: TTLCache


_RUNTIME: ContextVar[Optional[NodeRuntime]] = ContextVar("travel_graph_runtime", default=None)


def set_runtime(runtime: NodeRuntime) -> None:
    _RUNTIME.set(runtime)


def get_runtime() -> NodeRuntime:
    runtime = _RUNTIME.get()
    if runtime is None:
        raise RuntimeError(
            "TravelGraph runtime is not initialized. Call set_runtime(...) before invoking the graph."
        )
    return runtime


def timed_node(node_name: str) -> Callable:
    """Wrap a node function with structured timing + log emission.

    Each node returns a dict patch; we add `timings_ms` for that node.
    """
    def decorator(fn: Callable[..., Dict[str, Any]]) -> Callable[..., Dict[str, Any]]:
        @functools.wraps(fn)
        def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
            run_id = state.get("run_id", "-")
            thread_id = state.get("thread_id", "-")
            started = time.perf_counter()
            try:
                patch = fn(state) or {}
                duration_ms = (time.perf_counter() - started) * 1000.0
                logger.info(
                    "node.ok run_id=%s thread_id=%s node=%s duration_ms=%.1f",
                    run_id, thread_id, node_name, duration_ms,
                )
                timings = dict(patch.get("timings_ms") or {})
                timings[node_name] = duration_ms
                patch["timings_ms"] = timings
                return patch
            except Exception as exc:
                duration_ms = (time.perf_counter() - started) * 1000.0
                logger.exception(
                    "node.err run_id=%s thread_id=%s node=%s duration_ms=%.1f err=%s",
                    run_id, thread_id, node_name, duration_ms, exc,
                )
                raise
        return wrapper
    return decorator
