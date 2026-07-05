from __future__ import annotations

from pydantic import BaseModel


class TripSummary(BaseModel):
    id: str
    user_id: str
    query: str
    location: str
    date_str: str
    created_at: str
