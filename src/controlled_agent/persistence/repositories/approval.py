from __future__ import annotations

from uuid import uuid4

from controlled_agent.persistence.database import (
    Database,
)


class ApprovalRepository:
    """
    SQLite repository for human approval records.

    Security properties:

    - Approval is bound to one Agent run.
    - Approval is bound to one action.
    - Approval is bound to one order.
    - Approval is bound to an immutable context hash.
    - Decisions are immutable.
    - Approved requests can be consumed only once.

    Lifecycle:

        pending
            approved = NULL
            decided_at = NULL
            consumed_at = NULL

        approved
            approved = 1
            decided_at != NULL
            consumed_at = NULL

        consumed
            approved = 1
            decided_at != NULL
            consumed_at != NULL

        denied
            approved = 0
            decided_at != NULL
            consumed_at = NULL
    """

    def __init__(
        self,
        database: Database,
    ) -> None:
        self.database = database

    # ========================================================
    # VALIDATION
    # ========================================================

    @staticmethod
    def _validate_context(
        *,
        order_id: str,
        context_hash: str,
    ) -> None:

        if not order_id.strip():
            raise ValueError(
                "order_id is required "
                "for approval context."
            )

        if (
            len(context_hash) != 64
            or any(
                character
                not in "0123456789abcdef"
                for character
                in context_hash.lower()
            )
        ):
            raise ValueError(
                "context_hash must be a "
                "SHA-256 hex digest."
            )

    # ========================================================
    # CREATE REQUEST
    # ========================================================

    def create_request(
        self,
        *,
        run_id: str,
        action: str,
        order_id: str,
        context_hash: str,
        approval_id: str | None = None,
    ) -> dict:
        """
        Create a context-bound pending approval request.
        """

        self._validate_context(
            order_id=order_id,
            context_hash=context_hash,
        )

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
                    order_id,
                    context_hash,
                    approved,
                    decided_at,
                    consumed_at
                )
                VALUES (
                    ?, ?, ?, ?, ?,
                    NULL, NULL, NULL
                )
                """,
                (
                    generated_id,
                    run_id,
                    action,
                    order_id,
                    context_hash,
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

        with self.database.connect() as connection:

            row = connection.execute(
                """
                SELECT
                    approval_id,
                    run_id,
                    action,
                    order_id,
                    context_hash,
                    approved,
                    requested_at,
                    decided_at,
                    consumed_at
                FROM approvals
                WHERE approval_id = ?
                """,
                (
                    approval_id,
                ),
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
        Approve or deny a pending request.

        Decisions are immutable.
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
                    (
                        approval_id,
                    ),
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
    # CONSUME
    # ========================================================

    def consume(
        self,
        approval_id: str,
        *,
        run_id: str,
        action: str,
        order_id: str,
        context_hash: str,
    ) -> dict:
        """
        Consume one approved WRITE authorization.

        An approval cannot be:
        - consumed before approval,
        - consumed for another context,
        - consumed more than once.
        """

        self._validate_context(
            order_id=order_id,
            context_hash=context_hash,
        )

        with self.database.connect() as connection:

            cursor = connection.execute(
                """
                UPDATE approvals
                SET
                    consumed_at = CURRENT_TIMESTAMP
                WHERE approval_id = ?
                  AND run_id = ?
                  AND action = ?
                  AND order_id = ?
                  AND context_hash = ?
                  AND approved = 1
                  AND consumed_at IS NULL
                """,
                (
                    approval_id,
                    run_id,
                    action,
                    order_id,
                    context_hash,
                ),
            )

            if cursor.rowcount == 0:

                row = connection.execute(
                    """
                    SELECT
                        run_id,
                        action,
                        order_id,
                        context_hash,
                        approved,
                        consumed_at
                    FROM approvals
                    WHERE approval_id = ?
                    """,
                    (
                        approval_id,
                    ),
                ).fetchone()

                if row is None:
                    raise KeyError(
                        f"Unknown approval_id: "
                        f"{approval_id}"
                    )

                if (
                    row["run_id"] != run_id
                    or row["action"] != action
                    or row["order_id"] != order_id
                    or row["context_hash"]
                    != context_hash
                ):
                    raise ValueError(
                        "Approval context does not match."
                    )

                if row["approved"] != 1:
                    raise ValueError(
                        "Approval is not approved."
                    )

                if row["consumed_at"] is not None:
                    raise ValueError(
                        "Approval has already "
                        "been consumed."
                    )

                raise RuntimeError(
                    "Approval could not be consumed."
                )

        result = self.get(
            approval_id
        )

        if result is None:
            raise RuntimeError(
                "Approval was consumed but "
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

        with self.database.connect() as connection:

            rows = connection.execute(
                """
                SELECT
                    approval_id,
                    run_id,
                    action,
                    order_id,
                    context_hash,
                    approved,
                    requested_at,
                    decided_at,
                    consumed_at
                FROM approvals
                WHERE run_id = ?
                ORDER BY requested_at ASC, rowid ASC
                """,
                (
                    run_id,
                ),
            ).fetchall()

        return [
            self._row_to_dict(
                row
            )
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
        order_id: str | None = None,
        context_hash: str | None = None,
    ) -> dict | None:
        """
        Return the most recent un-decided request.

        Optional filters allow Runtime to require an
        exact WRITE authorization context.
        """

        conditions = [
            "run_id = ?",
            "approved IS NULL",
        ]

        parameters: list[object] = [
            run_id
        ]

        if action is not None:
            conditions.append(
                "action = ?"
            )
            parameters.append(
                action
            )

        if order_id is not None:
            conditions.append(
                "order_id = ?"
            )
            parameters.append(
                order_id
            )

        if context_hash is not None:
            conditions.append(
                "context_hash = ?"
            )
            parameters.append(
                context_hash
            )

        where_clause = (
            " AND ".join(
                conditions
            )
        )

        query = f"""
            SELECT
                approval_id,
                run_id,
                action,
                order_id,
                context_hash,
                approved,
                requested_at,
                decided_at,
                consumed_at
            FROM approvals
            WHERE {where_clause}
            ORDER BY requested_at DESC, rowid DESC
            LIMIT 1
        """

        with self.database.connect() as connection:

            row = connection.execute(
                query,
                tuple(parameters),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_dict(
            row
        )

    # ========================================================
    # LATEST APPROVED / UNCONSUMED
    # ========================================================

    def get_latest_approved_unconsumed(
        self,
        run_id: str,
        *,
        action: str,
        order_id: str,
        context_hash: str,
    ) -> dict | None:
        """
        Return the most recent approved WRITE authorization
        that exactly matches one execution context and has
        not yet been consumed.

        This lookup is intentionally strict and is intended
        for use immediately before a sensitive WRITE action.
        """

        self._validate_context(
            order_id=order_id,
            context_hash=context_hash,
        )

        with self.database.connect() as connection:

            row = connection.execute(
                """
                SELECT
                    approval_id,
                    run_id,
                    action,
                    order_id,
                    context_hash,
                    approved,
                    requested_at,
                    decided_at,
                    consumed_at
                FROM approvals
                WHERE run_id = ?
                  AND action = ?
                  AND order_id = ?
                  AND context_hash = ?
                  AND approved = 1
                  AND consumed_at IS NULL
                ORDER BY decided_at DESC, rowid DESC
                LIMIT 1
                """,
                (
                    run_id,
                    action,
                    order_id,
                    context_hash,
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

        with self.database.connect() as connection:

            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM approvals
                WHERE run_id = ?
                """,
                (
                    run_id,
                ),
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

        raw_approved = row[
            "approved"
        ]

        if raw_approved is None:
            approved: bool | None = None
        else:
            approved = bool(
                raw_approved
            )

        consumed_at = row[
            "consumed_at"
        ]

        if consumed_at is not None:
            status = "consumed"
        elif approved is True:
            status = "approved"
        elif approved is False:
            status = "denied"
        else:
            status = "pending"

        return {
            "approval_id": row[
                "approval_id"
            ],
            "run_id": row[
                "run_id"
            ],
            "action": row[
                "action"
            ],
            "order_id": row[
                "order_id"
            ],
            "context_hash": row[
                "context_hash"
            ],
            "approved": approved,
            "status": status,
            "requested_at": row[
                "requested_at"
            ],
            "decided_at": row[
                "decided_at"
            ],
            "consumed_at": (
                consumed_at
            ),
        }