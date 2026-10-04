from __future__ import annotations

from uuid import uuid4

from controlled_agent.domain.state import AgentState
from controlled_agent.persistence.database import Database


class AgentRunRepository:
    """
    Persistence repository for AgentState.

    Responsibilities:
    - Save a new Agent run
    - Update an existing Agent run
    - Restore AgentState from storage

    Runtime code should not need to know SQL details.
    """

    def __init__(
        self,
        database: Database,
    ) -> None:
        self.database = database

    def save(
        self,
        state: AgentState,
        *,
        run_id: str | None = None,
    ) -> str:
        """
        Insert or update an Agent run.

        If run_id is omitted, a new unique identifier
        is generated.

        Returns the run_id.
        """

        if run_id is None:
            run_id = str(uuid4())

        order_status = (
            state.order_status.value
            if state.order_status is not None
            else None
        )

        human_approved = (
            None
            if state.human_approved is None
            else int(state.human_approved)
        )

        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_runs (
                    run_id,
                    user_message,
                    latest_user_message,
                    order_id,
                    order_status,
                    days_delayed,
                    awaiting_approval,
                    human_approved,
                    ticket_id,
                    steps,
                    status,
                    finished,
                    awaiting_user_input,
                    final_message
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )

                ON CONFLICT(run_id)
                DO UPDATE SET
                    user_message = excluded.user_message,
                    latest_user_message = excluded.latest_user_message,
                    order_id = excluded.order_id,
                    order_status = excluded.order_status,
                    days_delayed = excluded.days_delayed,
                    awaiting_approval = excluded.awaiting_approval,
                    human_approved = excluded.human_approved,
                    ticket_id = excluded.ticket_id,
                    steps = excluded.steps,
                    status = excluded.status,
                    finished = excluded.finished,
                    awaiting_user_input = excluded.awaiting_user_input,
                    final_message = excluded.final_message,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    run_id,
                    state.user_message,
                    state.latest_user_message,
                    state.order_id,
                    order_status,
                    state.days_delayed,
                    int(state.awaiting_approval),
                    human_approved,
                    state.ticket_id,
                    state.steps,
                    state.status.value,
                    int(state.finished),
                    int(state.awaiting_user_input),
                    state.final_message,
                ),
            )

        return run_id

    def get(
        self,
        run_id: str,
    ) -> AgentState | None:
        """
        Load an AgentState by run_id.

        Returns None when the run does not exist.
        """

        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    user_message,
                    latest_user_message,
                    order_id,
                    order_status,
                    days_delayed,
                    awaiting_approval,
                    human_approved,
                    ticket_id,
                    steps,
                    status,
                    finished,
                    awaiting_user_input,
                    final_message
                FROM agent_runs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()

        if row is None:
            return None

        human_approved = (
            None
            if row["human_approved"] is None
            else bool(row["human_approved"])
        )

        return AgentState(
            user_message=row["user_message"],
            latest_user_message=row["latest_user_message"],
            order_id=row["order_id"],
            order_status=row["order_status"],
            days_delayed=row["days_delayed"],
            awaiting_approval=bool(
                row["awaiting_approval"]
            ),
            human_approved=human_approved,
            ticket_id=row["ticket_id"],
            steps=row["steps"],
            status=row["status"],
            finished=bool(row["finished"]),
            awaiting_user_input=bool(
                row["awaiting_user_input"]
            ),
            final_message=row["final_message"],
        )