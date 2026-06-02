from __future__ import annotations

from typing import Any, Dict

from core.date import normalize_user_date_to_iso
from core.graph.nodes.runtime import get_runtime, timed_node
from core.graph.state import GraphStatus, NodeErrorKind, make_error


@timed_node("resolve_location")
def resolve_location_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve user-provided raw_location into a canonical LocationResult.

    Single source of truth for location resolution + clarification semantics.
    Reads:  raw_location
    Writes: resolved_location, canonical_location, location_confidence,
            clarification_message, status, errors
    """
    raw_location = (state.get("raw_location") or "").strip()
    if not raw_location:
        return {
            "status": GraphStatus.NEEDS_CLARIFICATION.value,
            "clarification_message": "Please provide a destination.",
        }

    runtime = get_runtime()
    resolved = runtime.location_resolver.resolve(raw_location)
    clarification = runtime.location_resolver.clarification_message(raw_location, resolved)

    if clarification is None:
        return {
            "resolved_location": resolved.to_dict(),
            "canonical_location": resolved.canonical_name,
            "location_confidence": resolved.confidence,
            "status": GraphStatus.LOCATION_RESOLVED.value,
        }

    patch: Dict[str, Any] = {
        "status": GraphStatus.NEEDS_CLARIFICATION.value,
        "clarification_message": clarification,
    }
    if resolved is None:
        patch["errors"] = {
            "resolve_location": make_error(
                "resolve_location", NodeErrorKind.PROVIDER_UNAVAILABLE,
                "no candidate returned from geocoders",
            )
        }
    else:
        patch["resolved_location"] = resolved.to_dict()
        patch["canonical_location"] = resolved.canonical_name
        patch["location_confidence"] = resolved.confidence
    return patch


@timed_node("normalize_date")
def normalize_date_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize raw_date into ISO YYYY-MM-DD if not already provided.

    Reads:  raw_date, date_str
    Writes: date_str, status, errors
    """
    if state.get("date_str"):
        return {}
    raw_date = (state.get("raw_date") or "").strip()
    if not raw_date:
        return {
            "status": GraphStatus.FAILED.value,
            "errors": {
                "normalize_date": make_error(
                    "normalize_date", NodeErrorKind.NON_RETRYABLE, "missing date",
                )
            },
        }
    try:
        date_str = normalize_user_date_to_iso(raw_date)
    except ValueError as exc:
        return {
            "status": GraphStatus.FAILED.value,
            "errors": {
                "normalize_date": make_error(
                    "normalize_date", NodeErrorKind.NON_RETRYABLE, str(exc),
                )
            },
        }
    return {"date_str": date_str}
