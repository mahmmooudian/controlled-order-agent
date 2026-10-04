from __future__ import annotations

from uuid import uuid4

from controlled_agent.persistence.database import Database


class ApprovalRepository:
    """
    SQLite repository for human approval records.

    Approval lifecycle:

        pending
            approved = NULL
            decided_at = NULL

        approved
            approved = 1
            decided_at != NULL

        denied
            approved = 0
            decided_at != NULL

    Decisions are immutable. Once an approval request has
    been approved or denied, it cannot be changed.
    """

    def __init__(
        self,
        database: Database,
    ) -> None:
        self.database = database

    # ========================================================
    # CREATE REQUEST
    # ========================================================

    def create_request(
        self,
        *,
        run_id: str,
        action: str,
        approval_id: str | None = None,
    ) -> dict:
        """
        Create a new pending human approval request.

        The run_id must already exist in agent_runs because
        the database enforces a foreign-key relationship.
        """

        generated_id = (
            approval_id
            if approval_id is not None
            else str(uuid4())
        )

        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO approvals (
                    approval_id,
                    run_id,
                    action,
                    approved,
                    decided_at
                )
                VALUES (?, ?, ?, NULL, NULL)
                """,
                (
                    generated_id,
                    run_id,
                    action,
                ),
            )

        approval = self.get(
            generated_id
        )

        if approval is None:
            raise RuntimeError(
                "Approval request was created "
                "but could not be restored."
            )

        return approval

    # ========================================================
    # GET ONE
    # ========================================================

    def get(
        self,
        approval_id: str,
    ) -> dict | None:
        """
        Return one approval record.
        """

        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    approval_id,
                    run_id,
                    action,
                    approved,
                    requested_at,
                    decided_at
                FROM approvals
                WHERE approval_id = ?
                """,
                (approval_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_dict(
            row
        )

    # ========================================================
    # DECIDE
    # ========================================================

    def decide(
        self,
        approval_id: str,
        *,
        approved: bool,
    ) -> dict:
        """
        Approve or deny a pending approval request.

        Approval decisions are immutable:
        once decided, they cannot later be reversed.
        """

        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE approvals
                SET
                    approved = ?,
                    decided_at = CURRENT_TIMESTAMP
                WHERE approval_id = ?
                  AND approved IS NULL
                """,
                (
                    1 if approved else 0,
                    approval_id,
                ),
            )

            if cursor.rowcount == 0:
                row = connection.execute(
                    """
                    SELECT approved
                    FROM approvals
                    WHERE approval_id = ?
                    """,
                    (approval_id,),
                ).fetchone()

                if row is None:
                    raise KeyError(
                        f"Unknown approval_id: "
                        f"{approval_id}"
                    )

                raise ValueError(
                    "Approval has already been decided."
                )

        result = self.get(
            approval_id
        )

        if result is None:
            raise RuntimeError(
                "Approval was decided but "
                "could not be restored."
            )

        return result

    # ========================================================
    # GET FOR RUN
    # ========================================================

    def get_for_run(
        self,
        run_id: str,
    ) -> list[dict]:
        """
        Return approval history for one Agent run
        in creation order.
        """

        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    approval_id,
                    run_id,
                    action,
                    approved,
                    requested_at,
                    decided_at
                FROM approvals
                WHERE run_id = ?
                ORDER BY requested_at ASC, rowid ASC
                """,
                (run_id,),
            ).fetchall()

        return [
            self._row_to_dict(row)
            for row in rows
        ]

    # ========================================================
    # LATEST PENDING
    # ========================================================

    def get_latest_pending(
        self,
        run_id: str,
        *,
        action: str | None = None,
    ) -> dict | None:
        """
        Return the most recent pending approval
        for one Agent run.

        Optionally restrict the search to one action.
        """

        with self.database.connect() as connection:

            if action is None:
                row = connection.execute(
                    """
                    SELECT
                        approval_id,
                        run_id,
                        action,
                        approved,
                        requested_at,
                        decided_at
                    FROM approvals
                    WHERE run_id = ?
                      AND approved IS NULL
                    ORDER BY requested_at DESC, rowid DESC
                    LIMIT 1
                    """,
                    (run_id,),
                ).fetchone()

            else:
                row = connection.execute(
                    """
                    SELECT
                        approval_id,
                        run_id,
                        action,
                        approved,
                        requested_at,
                        decided_at
                    FROM approvals
                    WHERE run_id = ?
                      AND action = ?
                      AND approved IS NULL
                    ORDER BY requested_at DESC, rowid DESC
                    LIMIT 1
                    """,
                    (
                        run_id,
                        action,
                    ),
                ).fetchone()

        if row is None:
            return None

        return self._row_to_dict(
            row
        )

    # ========================================================
    # COUNT
    # ========================================================

    def count_for_run(
        self,
        run_id: str,
    ) -> int:
        """
        Return number of approval records
        belonging to one Agent run.
        """

        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM approvals
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()

        return int(
            row["count"]
        )

    # ========================================================
    # INTERNAL CONVERSION
    # ========================================================

    @staticmethod
    def _row_to_dict(
        row,
    ) -> dict:
        """
        Convert a SQLite row into a safe Python record.
        """

        raw_approved = row["approved"]

        if raw_approved is None:
            approved: bool | None = None
        else:
            approved = bool(
                raw_approved
            )

        return {
            "approval_id": row["approval_id"],
            "run_id": row["run_id"],
            "action": row["action"],
            "approved": approved,
            "requested_at": row["requested_at"],
            "decided_at": row["decided_at"],
        }