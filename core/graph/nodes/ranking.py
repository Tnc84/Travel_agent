from __future__ import annotations

from typing import Any, Dict, List

from core.graph.nodes.runtime import timed_node


def _rank_places(places: List[Dict]) -> List[Dict]:
    ranked: List[Dict] = []
    seen: set[str] = set()
    for item in places:
        name = (item.get("name") or "").strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        if not item.get("phone"):
            item["phone"] = None
        ranked.append(item)
    ranked.sort(
        key=lambda p: (
            0 if p.get("phone") else 1,
            p.get("distance_m", 999999.0),
        )
    )
    return ranked[:5]


@timed_node("rank_and_filter")
def rank_and_filter_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Deduplicate and rank POIs phone-first, distance second; cap at 5.

    Reads:  hotels, restaurants, attractions
    Writes: hotels, restaurants, attractions
    """
    return {
        "hotels": _rank_places(state.get("hotels") or []),
        "restaurants": _rank_places(state.get("restaurants") or []),
        "attractions": _rank_places(state.get("attractions") or []),
    }
