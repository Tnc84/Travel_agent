from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict


def persist_travel_guide(
    *,
    user_query: str,
    location: str,
    raw_date: str,
    final_state: Dict[str, Any],
    final_response: str,
) -> None:
    os.makedirs("history", exist_ok=True)
    filename = f"history/travel_guide_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "user_query": user_query,
                "location": location,
                "resolved_location": final_state.get("resolved_location"),
                "date": final_state.get("date_str") or raw_date,
                "status": final_state.get("status"),
                "run_id": final_state.get("run_id"),
                "thread_id": final_state.get("thread_id"),
                "final_response": final_response,
            },
            handle,
            indent=2,
        )
