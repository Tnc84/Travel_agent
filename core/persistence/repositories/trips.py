from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from core.persistence.schemas import TripSummary

from core.persistence.connection import db_connection


class TripRepository:
    def save_trip(
        self,
        *,
        user_id: str,
        query: str,
        location: str,
        date_str: str,
        response: str,
        resolved_location: Optional[Dict[str, Any]] = None,
        graph_run_id: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> str:
        trip_id = str(uuid.uuid4())
        with db_connection() as conn:
            conn.execute(
                """
                INSERT INTO app.saved_trips (
                    id, user_id, query, location, date_str,
                    resolved_location, response, graph_run_id, thread_id
                )
                VALUES (%s::uuid, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                """,
                (
                    trip_id,
                    user_id,
                    query,
                    location,
                    date_str,
                    json.dumps(resolved_location) if resolved_location else None,
                    response,
                    graph_run_id,
                    thread_id,
                ),
            )
            conn.commit()
        return trip_id

    def list_by_user(self, user_id: str, limit: int = 20) -> List[TripSummary]:
        with db_connection() as conn:
            rows = conn.execute(
                """
                SELECT id::text, user_id, query, location, date_str, created_at
                FROM app.saved_trips
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            ).fetchall()
        return [
            TripSummary(
                id=row["id"],
                user_id=row["user_id"],
                query=row["query"],
                location=row["location"],
                date_str=row["date_str"],
                created_at=row["created_at"].isoformat(),
            )
            for row in rows
        ]

    def get_by_id(self, trip_id: str) -> Optional[Dict[str, Any]]:
        with db_connection() as conn:
            row = conn.execute(
                """
                SELECT id::text, user_id, query, location, date_str,
                       resolved_location, response, graph_run_id, thread_id, created_at
                FROM app.saved_trips
                WHERE id = %s::uuid
                """,
                (trip_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "query": row["query"],
            "location": row["location"],
            "date_str": row["date_str"],
            "resolved_location": row["resolved_location"],
            "response": row["response"],
            "graph_run_id": row["graph_run_id"],
            "thread_id": row["thread_id"],
            "created_at": row["created_at"].isoformat(),
        }

    def add_favorite(self, user_id: str, trip_id: str) -> None:
        with db_connection() as conn:
            conn.execute(
                """
                INSERT INTO app.trip_favorites (user_id, trip_id)
                VALUES (%s, %s::uuid)
                ON CONFLICT (user_id, trip_id) DO NOTHING
                """,
                (user_id, trip_id),
            )
            conn.commit()

    def remove_favorite(self, user_id: str, trip_id: str) -> None:
        with db_connection() as conn:
            conn.execute(
                "DELETE FROM app.trip_favorites WHERE user_id = %s AND trip_id = %s::uuid",
                (user_id, trip_id),
            )
            conn.commit()
