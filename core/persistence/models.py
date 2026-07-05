from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class User:
    id: str
    external_id: Optional[str]
    display_name: Optional[str]
    created_at: datetime


@dataclass
class SavedTrip:
    id: str
    user_id: str
    query: str
    location: str
    date_str: str
    resolved_location: Optional[Dict[str, Any]]
    response: str
    graph_run_id: Optional[str]
    thread_id: Optional[str]
    created_at: datetime
