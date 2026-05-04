from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from core.location import LocationResult


class GraphStatus(str, Enum):
    PENDING = "pending"
    LOCATION_RESOLVED = "location_resolved"
    NEEDS_CLARIFICATION = "needs_clarification"
    DONE = "done"
    FAILED = "failed"


class NodeErrorKind(str, Enum):
    RETRYABLE = "retryable"
    NON_RETRYABLE = "non_retryable"
    TIMEOUT = "timeout"
    PROVIDER_UNAVAILABLE = "provider_unavailable"


class NodeError(TypedDict, total=False):
    node: str
    kind: str
    message: str
    provider: str


def _merge_errors(
    left: Dict[str, NodeError], right: Dict[str, NodeError]
) -> Dict[str, NodeError]:
    merged: Dict[str, NodeError] = dict(left or {})
    if right:
        merged.update(right)
    return merged


def _take_last(_left: Any, right: Any) -> Any:
    return right


class TravelGraphState(TypedDict, total=False):
    """Single source of truth for a travel graph run.

    All keys are explicit; nodes only read/write what they declare.
    Reducers (Annotated) are required for keys written by parallel branches.
    """

    user_input: str
    raw_location: str
    raw_date: str
    date_str: str

    resolved_location: Optional[Dict[str, Any]]
    canonical_location: Optional[str]
    location_confidence: Optional[float]
    clarification_message: Optional[str]

    weather: Annotated[Optional[Dict[str, Any]], _take_last]
    hotels: Annotated[List[Dict[str, Any]], _take_last]
    restaurants: Annotated[List[Dict[str, Any]], _take_last]
    attractions: Annotated[List[Dict[str, Any]], _take_last]

    final_response: Optional[str]
    used_tool_data: bool

    status: str
    errors: Annotated[Dict[str, NodeError], _merge_errors]

    run_id: str
    thread_id: str
    started_at: float
    finished_at: Optional[float]
    timings_ms: Annotated[Dict[str, float], lambda l, r: {**(l or {}), **(r or {})}]


def build_initial_state(
    *,
    user_input: str,
    raw_location: str,
    raw_date: str,
    date_str: str,
    resolved_location: Optional[LocationResult],
    run_id: str,
    thread_id: str,
    started_at: float,
) -> TravelGraphState:
    state: TravelGraphState = {
        "user_input": user_input,
        "raw_location": raw_location,
        "raw_date": raw_date,
        "date_str": date_str,
        "resolved_location": resolved_location.to_dict() if resolved_location else None,
        "canonical_location": resolved_location.canonical_name if resolved_location else None,
        "location_confidence": resolved_location.confidence if resolved_location else None,
        "clarification_message": None,
        "weather": None,
        "hotels": [],
        "restaurants": [],
        "attractions": [],
        "final_response": None,
        "used_tool_data": False,
        "status": GraphStatus.PENDING.value,
        "errors": {},
        "run_id": run_id,
        "thread_id": thread_id,
        "started_at": started_at,
        "finished_at": None,
        "timings_ms": {},
    }
    return state


def make_error(
    node: str, kind: NodeErrorKind, message: str, provider: Optional[str] = None
) -> NodeError:
    error: NodeError = {"node": node, "kind": kind.value, "message": message}
    if provider:
        error["provider"] = provider
    return error
