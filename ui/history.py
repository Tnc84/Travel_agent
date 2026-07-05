from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from core.persistence.config import load_persistence_config
from core.persistence.repositories.trips import TripRepository

logger = logging.getLogger(__name__)


def _default_user_id() -> str:
    return os.getenv("DEFAULT_USER_ID", "anonymous")


def persist_travel_guide(
    *,
    user_query: str,
    location: str,
    raw_date: str,
    final_state: Dict[str, Any],
    final_response: str,
    user_id: Optional[str] = None,
) -> Optional[str]:
    """Persist a travel guide to Postgres when configured, else JSON file."""
    cfg = load_persistence_config()
    date_str = final_state.get("date_str") or raw_date
    effective_user = user_id or _default_user_id()

    if cfg.enabled:
        try:
            trip_id = TripRepository().save_trip(
                user_id=effective_user,
                query=user_query,
                location=location,
                date_str=date_str,
                response=final_response,
                resolved_location=final_state.get("resolved_location"),
                graph_run_id=final_state.get("run_id"),
                thread_id=final_state.get("thread_id"),
            )
            logger.info("Saved trip %s for user %s", trip_id, effective_user)
            return trip_id
        except Exception as exc:
            logger.warning("DB persist failed, falling back to JSON: %s", exc)

    os.makedirs("history", exist_ok=True)
    filename = f"history/travel_guide_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "user_id": effective_user,
                "user_query": user_query,
                "location": location,
                "resolved_location": final_state.get("resolved_location"),
                "date": date_str,
                "status": final_state.get("status"),
                "run_id": final_state.get("run_id"),
                "thread_id": final_state.get("thread_id"),
                "final_response": final_response,
            },
            handle,
            indent=2,
        )
    return None
