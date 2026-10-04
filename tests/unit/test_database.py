from controlled_agent.persistence import Database


EXPECTED_TABLES = {
    "agent_runs",
    "tickets",
    "approvals",
    "audit_events",
}


def test_database_initialization_creates_expected_tables(
    tmp_path,
):
    db_path = tmp_path / "test.db"

    database = Database(
        db_path
    )

    database.initialize()

    assert (
        database.table_names()
        == EXPECTED_TABLES
    )


def test_database_initialization_is_idempotent(
    tmp_path,
):
    db_path = tmp_path / "test.db"

    database = Database(
        db_path
    )

    database.initialize()
    database.initialize()

    assert (
        database.table_names()
        == EXPECTED_TABLES
    )


def test_foreign_keys_are_enabled(
    tmp_path,
):
    database = Database(
        tmp_path / "test.db"
    )

    database.initialize()

    assert (
        database.foreign_keys_enabled()
        is True
    )


def test_database_file_is_created(
    tmp_path,
):
    db_path = tmp_path / "nested" / "test.db"

    database = Database(
        db_path
    )

    database.initialize()

    assert db_path.exists()