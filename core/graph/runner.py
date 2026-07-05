from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any, Dict, Iterator, Optional

from langgraph.checkpoint.base import BaseCheckpointSaver

from core.agent_platform import Coordinator
from core.graph.checkpoint import open_checkpointer
from core.graph.config import GraphRuntimeConfig, load_graph_config, validate_graph_config
from core.graph.graph_builder import build_travel_graph
from core.graph.nodes.runtime import NodeRuntime, set_runtime
from core.graph.state import GraphStatus, build_initial_state
from core.location import LocationResolver
from core.services.travel import build_travel_services

logger = logging.getLogger(__name__)


class TravelGraphRunner:
    """Holds the compiled graph and runtime resources for the lifetime of the process.

    Use as a context manager to ensure the Postgres connection is opened/closed
    cleanly on shutdown.
    """

    def __init__(
        self,
        coordinator: Coordinator,
        location_resolver: LocationResolver,
        config: Optional[GraphRuntimeConfig] = None,
    ):
        self._config = config or load_graph_config()
        validate_graph_config(self._config)
        self._coordinator = coordinator
        self._location_resolver = location_resolver
        self._cm = None
        self._checkpointer: Optional[BaseCheckpointSaver] = None
        self._graph = None
        self._runtime: Optional[NodeRuntime] = None
        self._lock = threading.Lock()

    @property
    def config(self) -> GraphRuntimeConfig:
        return self._config

    def __enter__(self) -> "TravelGraphRunner":
        self._cm = open_checkpointer(self._config)
        self._checkpointer = self._cm.__enter__()
        self._graph = build_travel_graph(
            self._checkpointer,
            step_timeout_seconds=self._config.global_timeout_seconds,
        )
        self._runtime = NodeRuntime(
            config=self._config,
            coordinator=self._coordinator,
            services=build_travel_services(self._config, self._location_resolver),
        )
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._cm is not None:
            self._cm.__exit__(exc_type, exc, tb)
            self._cm = None
            self._checkpointer = None
            self._graph = None
            self._runtime = None

    def _ensure_ready(self) -> None:
        if self._graph is None or self._runtime is None:
            raise RuntimeError("TravelGraphRunner is not started. Use within a `with` block.")

    def _new_ids(self, thread_id: Optional[str]) -> tuple[str, str]:
        return str(uuid.uuid4()), thread_id or str(uuid.uuid4())

    def _config_for_run(self, thread_id: str, run_id: str) -> Dict[str, Any]:
        return {
            "configurable": {"thread_id": thread_id},
            "metadata": {"run_id": run_id},
            "recursion_limit": 25,
        }

    def invoke(
        self,
        *,
        user_input: str,
        raw_location: str,
        raw_date: str,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._ensure_ready()
        run_id, thread_id = self._new_ids(thread_id)
        initial_state = build_initial_state(
            user_input=user_input,
            raw_location=raw_location,
            raw_date=raw_date,
            date_str="",
            resolved_location=None,
            run_id=run_id,
            thread_id=thread_id,
            started_at=time.time(),
        )
        with self._lock:
            set_runtime(self._runtime)
            logger.info(
                "graph.invoke.start run_id=%s thread_id=%s location=%r date=%r",
                run_id, thread_id, raw_location, raw_date,
            )
            final_state = self._graph.invoke(
                initial_state,
                config=self._config_for_run(thread_id, run_id),
            )
            logger.info(
                "graph.invoke.end run_id=%s thread_id=%s status=%s timings_ms=%s",
                run_id, thread_id, final_state.get("status"), final_state.get("timings_ms"),
            )
            return final_state

    def stream_events(
        self,
        *,
        user_input: str,
        raw_location: str,
        raw_date: str,
        thread_id: Optional[str] = None,
    ) -> Iterator[tuple[str, Dict[str, Any]]]:
        """Yield ``(event_name, payload)`` tuples for SSE adapters.

        Maps node-level state updates into UX-friendly events that match the legacy
        contract: ``location_resolved``, ``weather_ready``, ``hotels_ready``,
        ``restaurants_ready``, ``attractions_ready``, ``final_message``, ``done``.
        """
        self._ensure_ready()
        run_id, thread_id = self._new_ids(thread_id)
        initial_state = build_initial_state(
            user_input=user_input,
            raw_location=raw_location,
            raw_date=raw_date,
            date_str="",
            resolved_location=None,
            run_id=run_id,
            thread_id=thread_id,
            started_at=time.time(),
        )
        emitted: set[str] = set()
        accumulated: Dict[str, Any] = dict(initial_state)
        with self._lock:
            set_runtime(self._runtime)
            logger.info(
                "graph.stream.start run_id=%s thread_id=%s location=%r date=%r",
                run_id, thread_id, raw_location, raw_date,
            )
            for chunk in self._graph.stream(
                initial_state,
                config=self._config_for_run(thread_id, run_id),
                stream_mode="values",
            ):
                accumulated.update(chunk)
                for event_name, payload in _project_events(chunk, emitted):
                    yield event_name, payload

            for event_name, payload in _project_terminal_events(accumulated, emitted):
                yield event_name, payload
            logger.info(
                "graph.stream.end run_id=%s thread_id=%s status=%s",
                run_id, thread_id, accumulated.get("status"),
            )


def _project_events(
    chunk: Dict[str, Any], emitted: set[str]
) -> Iterator[tuple[str, Dict[str, Any]]]:
    if "location_resolved" not in emitted and chunk.get("resolved_location"):
        emitted.add("location_resolved")
        yield "location_resolved", {
            "location": chunk["resolved_location"],
            "date": chunk.get("date_str"),
        }
    if "weather_ready" not in emitted and chunk.get("weather"):
        emitted.add("weather_ready")
        yield "weather_ready", chunk["weather"]
    if "hotels_ready" not in emitted and chunk.get("hotels"):
        emitted.add("hotels_ready")
        yield "hotels_ready", {"items": chunk["hotels"]}
    if "restaurants_ready" not in emitted and chunk.get("restaurants"):
        emitted.add("restaurants_ready")
        yield "restaurants_ready", {"items": chunk["restaurants"]}
    if "attractions_ready" not in emitted and chunk.get("attractions"):
        emitted.add("attractions_ready")
        yield "attractions_ready", {"items": chunk["attractions"]}


def _project_terminal_events(
    final_state: Dict[str, Any], emitted: set[str]
) -> Iterator[tuple[str, Dict[str, Any]]]:
    errors = final_state.get("errors") or {}
    for section_key, event_name in (
        ("weather", "weather_ready"),
        ("hotels", "hotels_ready"),
        ("restaurants", "restaurants_ready"),
        ("attractions", "attractions_ready"),
    ):
        if event_name in emitted:
            continue
        section_value = final_state.get(section_key)
        if not section_value:
            error_for_section = _section_error(section_key, errors)
            yield event_name, {"error": error_for_section} if error_for_section else {"items": []}
            emitted.add(event_name)

    response = final_state.get("final_response")
    if response is not None and "final_message" not in emitted:
        emitted.add("final_message")
        yield "final_message", {"response": response}

    if "done" not in emitted:
        emitted.add("done")
        yield "done", {
            "ok": final_state.get("status") == GraphStatus.DONE.value,
            "run_id": final_state.get("run_id"),
            "thread_id": final_state.get("thread_id"),
        }


def _section_error(section_key: str, errors: Dict[str, Any]) -> Optional[str]:
    mapping = {
        "weather": "fetch_weather",
        "hotels": "fetch_poi",
        "restaurants": "fetch_poi",
        "attractions": "fetch_poi",
    }
    err = errors.get(mapping.get(section_key, ""))
    if not err:
        return None
    return err.get("message") if isinstance(err, dict) else str(err)
