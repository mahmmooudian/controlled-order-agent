from __future__ import annotations

from controlled_agent.observability import AuditEvent
from controlled_agent.persistence.database import Database


class AuditRepository:
    """
    SQLite repository for operational audit events.

    Responsibilities:
    - Persist AuditEvent records
    - Associate events with an Agent run
    - Restore an execution trace in original order
    """

    def __init__(
        self,
        database: Database,
    ) -> None:
        self.database = database

    def add(
        self,
        event: AuditEvent,
        *,
        run_id: str | None = None,
    ) -> int:
        """
        Persist one audit event.

        Returns the generated database row id.
        """

        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO audit_events (
                    run_id,
                    step,
                    event,
                    detail,
                    timestamp
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    event.step,
                    event.event,
                    event.detail,
                    event.timestamp,
                ),
            )

            event_id = cursor.lastrowid

        if event_id is None:
            raise RuntimeError(
                "Audit event was stored without an id."
            )

        return int(event_id)

    def get_for_run(
        self,
        run_id: str,
    ) -> list[AuditEvent]:
        """
        Return all audit events for one Agent run
        in original insertion order.
        """

        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    timestamp,
                    step,
                    event,
                    detail
                FROM audit_events
                WHERE run_id = ?
                ORDER BY id ASC
                """,
                (run_id,),
            ).fetchall()

        return [
            AuditEvent(
                timestamp=row["timestamp"],
                step=row["step"],
                event=row["event"],
                detail=row["detail"],
            )
            for row in rows
        ]

    def count_for_run(
        self,
        run_id: str,
    ) -> int:
        """
        Return number of stored events for a run.
        """

        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM audit_events
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()

        return int(row["count"])

    def clear_for_run(
        self,
        run_id: str,
    ) -> None:
        """
        Remove all audit events belonging to one run.
        """

        with self.database.connect() as connection:
            connection.execute(
                """
                DELETE FROM audit_events
                WHERE run_id = ?
                """,
                (run_id,),
            )