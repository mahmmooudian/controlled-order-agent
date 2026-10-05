import sqlite3

from controlled_agent.persistence import (
    ApprovalRepository,
    Database,
)


LEGACY_SCHEMA = """
CREATE TABLE agent_runs (
    run_id TEXT PRIMARY KEY,

    user_message TEXT NOT NULL,
    latest_user_message TEXT,

    order_id TEXT,
    order_status TEXT,
    days_delayed INTEGER,

    awaiting_approval INTEGER NOT NULL DEFAULT 0,
    human_approved INTEGER,

    ticket_id TEXT,

    steps INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,

    finished INTEGER NOT NULL DEFAULT 0,
    awaiting_user_input INTEGER NOT NULL DEFAULT 0,

    final_message TEXT,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE approvals (
    approval_id TEXT PRIMARY KEY,

    run_id TEXT NOT NULL,

    action TEXT NOT NULL,

    approved INTEGER,

    requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decided_at TEXT,

    FOREIGN KEY (run_id)
        REFERENCES agent_runs(run_id)
        ON DELETE CASCADE
);
"""


def create_legacy_database(
    db_path,
) -> None:
    connection = sqlite3.connect(
        str(db_path)
    )

    try:
        connection.executescript(
            LEGACY_SCHEMA
        )

        connection.execute(
            """
            INSERT INTO agent_runs (
                run_id,
                user_message,
                latest_user_message,
                status
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "legacy-run",
                "Check order 8452.",
                "Check order 8452.",
                "waiting_for_approval",
            ),
        )

        connection.execute(
            """
            INSERT INTO approvals (
                approval_id,
                run_id,
                action,
                approved
            )
            VALUES (?, ?, ?, NULL)
            """,
            (
                "legacy-approval",
                "legacy-run",
                "create_ticket",
            ),
        )

        connection.commit()

    finally:
        connection.close()


def test_legacy_approval_schema_is_migrated(
    tmp_path,
):
    db_path = (
        tmp_path
        / "legacy-approval.db"
    )

    create_legacy_database(
        db_path
    )

    database = Database(
        db_path
    )

    database.initialize()

    connection = database.connect()

    try:
        rows = connection.execute(
            """
            PRAGMA table_info(approvals);
            """
        ).fetchall()

        columns = {
            row["name"]
            for row in rows
        }

    finally:
        connection.close()

    assert "order_id" in columns
    assert "context_hash" in columns
    assert "consumed_at" in columns


def test_legacy_approval_record_is_preserved(
    tmp_path,
):
    db_path = (
        tmp_path
        / "legacy-record.db"
    )

    create_legacy_database(
        db_path
    )

    database = Database(
        db_path
    )

    database.initialize()

    repository = ApprovalRepository(
        database
    )

    approval = repository.get(
        "legacy-approval"
    )

    assert approval is not None

    assert (
        approval["approval_id"]
        == "legacy-approval"
    )

    assert (
        approval["run_id"]
        == "legacy-run"
    )

    assert (
        approval["action"]
        == "create_ticket"
    )

    assert (
        approval["approved"]
        is None
    )

    assert (
        approval["order_id"]
        is None
    )

    assert (
        approval["context_hash"]
        is None
    )

    assert (
        approval["consumed_at"]
        is None
    )


def test_legacy_approval_cannot_match_new_context(
    tmp_path,
):
    db_path = (
        tmp_path
        / "legacy-fail-closed.db"
    )

    create_legacy_database(
        db_path
    )

    database = Database(
        db_path
    )

    database.initialize()

    repository = ApprovalRepository(
        database
    )

    approval = (
        repository.get_latest_pending(
            "legacy-run",
            action="create_ticket",
            order_id="8452",
            context_hash="a" * 64,
        )
    )

    assert approval is None


def test_new_context_bound_approval_can_be_created_after_migration(
    tmp_path,
):
    db_path = (
        tmp_path
        / "legacy-new-request.db"
    )

    create_legacy_database(
        db_path
    )

    database = Database(
        db_path
    )

    database.initialize()

    repository = ApprovalRepository(
        database
    )

    approval = repository.create_request(
        run_id="legacy-run",
        action="create_ticket",
        order_id="8452",
        context_hash="a" * 64,
    )

    assert (
        approval["order_id"]
        == "8452"
    )

    assert (
        approval["context_hash"]
        == "a" * 64
    )

    assert (
        approval["status"]
        == "pending"
    )


def test_database_initialize_is_idempotent_after_migration(
    tmp_path,
):
    db_path = (
        tmp_path
        / "legacy-idempotent.db"
    )

    create_legacy_database(
        db_path
    )

    database = Database(
        db_path
    )

    database.initialize()
    database.initialize()

    connection = database.connect()

    try:
        rows = connection.execute(
            """
            PRAGMA table_info(approvals);
            """
        ).fetchall()

        column_names = [
            row["name"]
            for row in rows
        ]

    finally:
        connection.close()

    assert (
        column_names.count(
            "order_id"
        )
        == 1
    )

    assert (
        column_names.count(
            "context_hash"
        )
        == 1
    )

    assert (
        column_names.count(
            "consumed_at"
        )
        == 1
    )