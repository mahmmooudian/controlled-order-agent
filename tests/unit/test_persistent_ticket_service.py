from controlled_agent.adapters.sqlite import (
    PersistentTicketService,
)
from controlled_agent.persistence import (
    Database,
    TicketRepository,
)
from controlled_agent.tools.ticket import create_ticket


def create_service(tmp_path):
    database = Database(
        tmp_path / "tickets.db"
    )

    database.initialize()

    repository = TicketRepository(
        database
    )

    service = PersistentTicketService(
        repository
    )

    return service, repository


def test_persistent_service_creates_ticket(
    tmp_path,
):
    service, repository = create_service(
        tmp_path
    )

    result = service.create_ticket(
        order_id="8452",
        reason="Order delayed 5 days",
        idempotency_key="persistent-test",
    )

    assert result["ticket_id"] == "TCK-1001"
    assert result["status"] == "created"

    assert repository.count() == 1


def test_persistent_service_is_idempotent(
    tmp_path,
):
    service, repository = create_service(
        tmp_path
    )

    first = service.create_ticket(
        order_id="8452",
        reason="Order delayed 5 days",
        idempotency_key="same-key",
    )

    second = service.create_ticket(
        order_id="8452",
        reason="Order delayed 5 days",
        idempotency_key="same-key",
    )

    assert first["ticket_id"] == second["ticket_id"]
    assert first["status"] == "created"
    assert second["status"] == "existing"

    assert repository.count() == 1


def test_ticket_survives_new_service_instance(
    tmp_path,
):
    db_path = tmp_path / "persistent.db"

    first_database = Database(
        db_path
    )
    first_database.initialize()

    first_service = PersistentTicketService(
        TicketRepository(first_database)
    )

    created = first_service.create_ticket(
        order_id="8452",
        reason="Persistent ticket",
        idempotency_key="restart-key",
    )

    second_database = Database(
        db_path
    )

    second_service = PersistentTicketService(
        TicketRepository(second_database)
    )

    existing = second_service.create_ticket(
        order_id="8452",
        reason="Persistent ticket",
        idempotency_key="restart-key",
    )

    assert (
        existing["ticket_id"]
        == created["ticket_id"]
    )

    assert existing["status"] == "existing"


def test_tool_accepts_persistent_ticket_service(
    tmp_path,
):
    service, repository = create_service(
        tmp_path
    )

    result = create_ticket(
        order_id="8452",
        reason="Order delayed 5 days",
        idempotency_key="tool-persistent",
        service=service,
    )

    assert result.ticket_id == "TCK-1001"
    assert result.status == "created"

    assert repository.count() == 1