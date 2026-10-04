from __future__ import annotations

import sqlite3
from typing import Any

from controlled_agent.persistence.database import Database


class TicketRepository:
    """
    SQLite repository for support tickets.

    Responsibilities:
    - Persist tickets
    - Enforce idempotency
    - Return an existing ticket for duplicate requests
    - Retrieve tickets from persistent storage
    """

    def __init__(
        self,
        database: Database,
    ) -> None:
        self.database = database

    def create(
        self,
        *,
        order_id: str,
        reason: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """
        Create a ticket or return an existing one
        when the same idempotency_key is reused.
        """

        with self.database.connect() as connection:
            existing = connection.execute(
                """
                SELECT
                    ticket_id,
                    order_id,
                    reason,
                    idempotency_key,
                    status
                FROM tickets
                WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()

            if existing is not None:
                return {
                    "ticket_id": existing["ticket_id"],
                    "order_id": existing["order_id"],
                    "reason": existing["reason"],
                    "idempotency_key": existing[
                        "idempotency_key"
                    ],
                    "status": "existing",
                }

            ticket_number = (
                connection.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM tickets
                    """
                ).fetchone()["count"]
                + 1001
            )

            ticket_id = f"TCK-{ticket_number}"

            try:
                connection.execute(
                    """
                    INSERT INTO tickets (
                        ticket_id,
                        order_id,
                        reason,
                        idempotency_key,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        ticket_id,
                        order_id,
                        reason,
                        idempotency_key,
                        "created",
                    ),
                )

            except sqlite3.IntegrityError:
                existing = connection.execute(
                    """
                    SELECT
                        ticket_id,
                        order_id,
                        reason,
                        idempotency_key,
                        status
                    FROM tickets
                    WHERE idempotency_key = ?
                    """,
                    (idempotency_key,),
                ).fetchone()

                if existing is None:
                    raise

                return {
                    "ticket_id": existing["ticket_id"],
                    "order_id": existing["order_id"],
                    "reason": existing["reason"],
                    "idempotency_key": existing[
                        "idempotency_key"
                    ],
                    "status": "existing",
                }

        return {
            "ticket_id": ticket_id,
            "order_id": order_id,
            "reason": reason,
            "idempotency_key": idempotency_key,
            "status": "created",
        }

    def get_by_id(
        self,
        ticket_id: str,
    ) -> dict[str, Any] | None:
        """
        Retrieve a ticket by ticket_id.
        """

        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    ticket_id,
                    order_id,
                    reason,
                    idempotency_key,
                    status
                FROM tickets
                WHERE ticket_id = ?
                """,
                (ticket_id,),
            ).fetchone()

        if row is None:
            return None

        return dict(row)

    def get_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> dict[str, Any] | None:
        """
        Retrieve a ticket using its idempotency key.
        """

        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    ticket_id,
                    order_id,
                    reason,
                    idempotency_key,
                    status
                FROM tickets
                WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()

        if row is None:
            return None

        return dict(row)

    def count(
        self,
    ) -> int:
        """
        Return the number of stored tickets.
        """

        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM tickets
                """
            ).fetchone()

        return int(row["count"])