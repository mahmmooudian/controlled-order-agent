from controlled_agent.adapters.sqlite import (
    PersistentTicketService,
)
from controlled_agent.observability import AuditLogger
from controlled_agent.persistence import (
    Database,
    TicketRepository,
)
from controlled_agent.planners import RuleBasedPlanner
from controlled_agent.runtime import ControlledOrderAgent


def test_runtime_accepts_injected_audit_logger():
    audit = AuditLogger()

    agent = ControlledOrderAgent(
        RuleBasedPlanner(),
        audit_logger=audit,
    )

    assert agent.audit is audit

    state = agent.run(
        "Check order 45821."
    )

    assert state.finished is True

    events = [
        item.event
        for item in audit.get_events()
    ]

    assert "request_received" in events
    assert "final_response" in events


def test_runtime_uses_persistent_ticket_service(
    tmp_path,
):
    database = Database(
        tmp_path / "agent.db"
    )
    database.initialize()

    repository = TicketRepository(
        database
    )

    service = PersistentTicketService(
        repository
    )

    agent = ControlledOrderAgent(
        RuleBasedPlanner(),
        ticket_service=service,
    )

    state = agent.run(
        "Check order 8452."
    )

    assert state.awaiting_approval is True
    assert repository.count() == 0

    state = agent.resume_with_approval(
        state,
        approved=True,
    )

    assert state.finished is True
    assert state.ticket_id == "TCK-1001"

    assert repository.count() == 1

    stored = repository.get_by_id(
        "TCK-1001"
    )

    assert stored is not None
    assert stored["order_id"] == "8452"


def test_persistent_ticket_survives_new_agent_instance(
    tmp_path,
):
    db_path = (
        tmp_path
        / "persistent-agent.db"
    )

    # --------------------------------------------------------
    # FIRST AGENT INSTANCE
    # --------------------------------------------------------

    first_database = Database(
        db_path
    )
    first_database.initialize()

    first_repository = TicketRepository(
        first_database
    )

    first_service = PersistentTicketService(
        first_repository
    )

    first_agent = ControlledOrderAgent(
        RuleBasedPlanner(),
        ticket_service=first_service,
    )

    first_state = first_agent.run(
        "Check order 8452."
    )

    assert first_state.awaiting_approval is True

    first_state = (
        first_agent.resume_with_approval(
            first_state,
            approved=True,
        )
    )

    assert first_state.finished is True
    assert first_state.ticket_id == "TCK-1001"

    assert first_repository.count() == 1

    first_ticket_id = (
        first_state.ticket_id
    )

    # --------------------------------------------------------
    # SECOND AGENT INSTANCE
    # SAME SQLITE DATABASE
    # --------------------------------------------------------

    second_database = Database(
        db_path
    )

    second_repository = TicketRepository(
        second_database
    )

    second_service = PersistentTicketService(
        second_repository
    )

    second_agent = ControlledOrderAgent(
        RuleBasedPlanner(),
        ticket_service=second_service,
    )

    second_state = second_agent.run(
        "Check order 8452."
    )

    assert second_state.awaiting_approval is True

    second_state = (
        second_agent.resume_with_approval(
            second_state,
            approved=True,
        )
    )

    assert second_state.finished is True

    # Same idempotency key must return
    # the original persistent ticket.
    assert (
        second_state.ticket_id
        == first_ticket_id
    )

    # Database must still contain only one ticket.
    assert second_repository.count() == 1