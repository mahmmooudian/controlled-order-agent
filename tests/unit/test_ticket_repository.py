from controlled_agent.persistence import (
    Database,
    TicketRepository,
)


def create_repository(tmp_path):
    database = Database(
        tmp_path / "tickets.db"
    )

    database.initialize()

    return TicketRepository(
        database
    )


def test_ticket_can_be_created(
    tmp_path,
):
    repository = create_repository(
        tmp_path
    )

    ticket = repository.create(
        order_id="8452",
        reason="Order delayed 5 days",
        idempotency_key="ticket:8452:delay",
    )

    assert ticket["ticket_id"] == "TCK-1001"
    assert ticket["order_id"] == "8452"
    assert ticket["status"] == "created"

    assert repository.count() == 1


def test_duplicate_idempotency_key_returns_existing_ticket(
    tmp_path,
):
    repository = create_repository(
        tmp_path
    )

    first = repository.create(
        order_id="8452",
        reason="Order delayed 5 days",
        idempotency_key="same-key",
    )

    second = repository.create(
        order_id="8452",
        reason="Order delayed 5 days",
        idempotency_key="same-key",
    )

    assert first["ticket_id"] == second["ticket_id"]

    assert first["status"] == "created"
    assert second["status"] == "existing"

    assert repository.count() == 1


def test_different_idempotency_keys_create_different_tickets(
    tmp_path,
):
    repository = create_repository(
        tmp_path
    )

    first = repository.create(
        order_id="8452",
        reason="First ticket",
        idempotency_key="key-a",
    )

    second = repository.create(
        order_id="8452",
        reason="Second ticket",
        idempotency_key="key-b",
    )

    assert first["ticket_id"] == "TCK-1001"
    assert second["ticket_id"] == "TCK-1002"

    assert repository.count() == 2


def test_ticket_can_be_loaded_by_id(
    tmp_path,
):
    repository = create_repository(
        tmp_path
    )

    created = repository.create(
        order_id="8452",
        reason="Delayed order",
        idempotency_key="load-test",
    )

    loaded = repository.get_by_id(
        created["ticket_id"]
    )

    assert loaded is not None
    assert loaded["ticket_id"] == "TCK-1001"
    assert loaded["order_id"] == "8452"
    assert loaded["idempotency_key"] == "load-test"


def test_ticket_can_be_loaded_by_idempotency_key(
    tmp_path,
):
    repository = create_repository(
        tmp_path
    )

    repository.create(
        order_id="8452",
        reason="Delayed order",
        idempotency_key="lookup-key",
    )

    loaded = repository.get_by_idempotency_key(
        "lookup-key"
    )

    assert loaded is not None
    assert loaded["ticket_id"] == "TCK-1001"
    assert loaded["order_id"] == "8452"


def test_unknown_ticket_returns_none(
    tmp_path,
):
    repository = create_repository(
        tmp_path
    )

    assert (
        repository.get_by_id("TCK-9999")
        is None
    )

    assert (
        repository.get_by_idempotency_key(
            "missing-key"
        )
        is None
    )


def test_ticket_persists_across_repository_instances(
    tmp_path,
):
    db_path = tmp_path / "persistent.db"

    database = Database(
        db_path
    )
    database.initialize()

    first_repository = TicketRepository(
        database
    )

    created = first_repository.create(
        order_id="8452",
        reason="Persistent ticket",
        idempotency_key="persistent-key",
    )

    second_repository = TicketRepository(
        Database(db_path)
    )

    loaded = (
        second_repository
        .get_by_idempotency_key(
            "persistent-key"
        )
    )

    assert loaded is not None
    assert (
        loaded["ticket_id"]
        == created["ticket_id"]
    )