from __future__ import annotations

import logging
import time
from typing import Any, Dict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from core.graph.nodes import (
    fallback_response_node,
    fetch_poi_node,
    fetch_weather_node,
    normalize_date_node,
    rank_and_filter_node,
    resolve_location_node,
    synthesize_response_node,
)
from core.graph.state import GraphStatus, TravelGraphState

logger = logging.getLogger(__name__)


def _route_after_location(state: Dict[str, Any]) -> str:
    """Conditional edge: clarification path vs continue with normalize_date."""
    if state.get("status") == GraphStatus.NEEDS_CLARIFICATION.value:
        return "clarify"
    return "continue"


def _route_after_normalize(state: Dict[str, Any]):
    """Either clarify (terminal) or fan-out to weather + POI in parallel."""
    if state.get("status") == GraphStatus.FAILED.value:
        return "clarify"
    return ["fetch_weather", "fetch_poi"]


def _clarification_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Terminal node when location is ambiguous or date is invalid."""
    message = state.get("clarification_message")
    if not message:
        errors = state.get("errors") or {}
        norm_err = errors.get("normalize_date") or {}
        if norm_err:
            message = f"Date error: {norm_err.get('message', 'invalid date')}"
        else:
            message = "I could not process this travel request. Please try again."
    return {
        "final_response": message,
        "used_tool_data": False,
        "status": GraphStatus.DONE.value,
        "finished_at": time.time(),
    }


def _route_after_rank(state: Dict[str, Any]) -> str:
    """Conditional edge: synthesize when any data, fallback otherwise."""
    has_data = bool(
        state.get("weather")
        or state.get("hotels")
        or state.get("restaurants")
        or state.get("attractions")
    )
    return "synthesize" if has_data else "fallback"


def build_travel_graph(
    checkpointer: BaseCheckpointSaver,
    step_timeout_seconds: float | None = None,
):
    """Compile the travel graph with conditional edges and parallel POI/weather branches.

    `step_timeout_seconds`, when set, applies a per-super-step wall-clock guardrail
    enforced by LangGraph (graph-global reliability budget on top of per-node timeouts).
    """
    graph = StateGraph(TravelGraphState)

    graph.add_node("resolve_location", resolve_location_node)
    graph.add_node("normalize_date", normalize_date_node)
    graph.add_node("clarify", _clarification_node)
    graph.add_node("fetch_weather", fetch_weather_node)
    graph.add_node("fetch_poi", fetch_poi_node)
    graph.add_node("rank_and_filter", rank_and_filter_node)
    graph.add_node("synthesize", synthesize_response_node)
    graph.add_node("fallback", fallback_response_node)

    graph.add_edge(START, "resolve_location")
    graph.add_conditional_edges(
        "resolve_location",
        _route_after_location,
        {"continue": "normalize_date", "clarify": "clarify"},
    )
    graph.add_conditional_edges(
        "normalize_date",
        _route_after_normalize,
        ["fetch_weather", "fetch_poi", "clarify"],
    )
    graph.add_edge("fetch_weather", "rank_and_filter")
    graph.add_edge("fetch_poi", "rank_and_filter")
    graph.add_conditional_edges(
        "rank_and_filter",
        _route_after_rank,
        {"synthesize": "synthesize", "fallback": "fallback"},
    )
    graph.add_edge("clarify", END)
    graph.add_edge("synthesize", END)
    graph.add_edge("fallback", END)

    compiled = graph.compile(checkpointer=checkpointer)
    if step_timeout_seconds and step_timeout_seconds > 0:
        compiled.step_timeout = step_timeout_seconds
    logger.info(
        "Travel graph compiled (checkpointer=%s, step_timeout_s=%s)",
        type(checkpointer).__name__, step_timeout_seconds,
    )
    return compiled
