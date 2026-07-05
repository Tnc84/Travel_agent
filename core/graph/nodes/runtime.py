from __future__ import annotations

import functools
import logging
import time
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from core.agent_platform import Coordinator
from core.graph.config import GraphRuntimeConfig
from core.services.travel import TTLCache, TravelServices, build_travel_services

logger = logging.getLogger(__name__)

# Re-export for backward compatibility with any external imports.
__all__ = ["NodeRuntime", "TTLCache", "get_runtime", "set_runtime", "timed_node"]


@dataclass
class NodeRuntime:
    """Shared, node-visible runtime resources injected via ContextVar.

    Nodes never construct providers/clients themselves; they pull from runtime.
    """
    config: GraphRuntimeConfig
    coordinator: Coordinator
    services: TravelServices


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
