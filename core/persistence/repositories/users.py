from __future__ import annotations

import uuid
from typing import Optional

from core.persistence.connection import db_connection
from core.persistence.models import User


class UserRepository:
    def get_or_create(self, user_id: str, display_name: Optional[str] = None) -> User:
        with db_connection() as conn:
            row = conn.execute(
                "SELECT id::text, external_id, display_name, created_at FROM app.users WHERE external_id = %s",
                (user_id,),
            ).fetchone()
            if row:
                return User(
                    id=row["id"],
                    external_id=row["external_id"],
                    display_name=row["display_name"],
                    created_at=row["created_at"],
                )
            new_id = str(uuid.uuid4())
            row = conn.execute(
                """
                INSERT INTO app.users (id, external_id, display_name)
                VALUES (%s::uuid, %s, %s)
                RETURNING id::text, external_id, display_name, created_at
                """,
                (new_id, user_id, display_name or user_id),
            ).fetchone()
            conn.commit()
            return User(
                id=row["id"],
                external_id=row["external_id"],
                display_name=row["display_name"],
                created_at=row["created_at"],
            )
