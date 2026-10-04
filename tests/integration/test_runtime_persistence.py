from controlled_agent.adapters.sqlite import (
    PersistentTicketService,
)
from controlled_agent.persistence import (
    AgentRunRepository,
    Database,
    TicketRepository,
)
from controlled_agent.planners import RuleBasedPlanner
from controlled_agent.runtime import ControlledOrderAgent


def test_runtime_persists_waiting_for_approval_state(
    tmp_path,
):
    database = Database(
        tmp_path / "agent-runs.db"
    )
    database.initialize()

    run_repository = AgentRunRepository(
        database
    )

    agent = ControlledOrderAgent(
        RuleBasedPlanner(),
        run_repository=run_repository,
    )

    state = agent.run(
        "Check order 8452."
    )

    assert state.awaiting_approval is True

    assert agent.current_run_id is not None

    stored = run_repository.get(
        agent.current_run_id
    )

    assert stored is not None
    assert stored.order_id == "8452"
    assert stored.days_delayed == 5
    assert stored.awaiting_approval is True
    assert stored.finished is False


def test_runtime_restores_and_resumes_run_after_restart(
    tmp_path,
):
    db_path = (
        tmp_path
        / "restart.db"
    )

    # ========================================================
    # FIRST AGENT INSTANCE
    # ========================================================

    first_database = Database(
        db_path
    )
    first_database.initialize()

    first_run_repository = AgentRunRepository(
        first_database
    )

    first_agent = ControlledOrderAgent(
        RuleBasedPlanner(),
        run_repository=first_run_repository,
    )

    state = first_agent.run(
        "Check order 8452."
    )

    assert state.awaiting_approval is True

    assert (
        first_agent.current_run_id
        is not None
    )

    run_id = (
        first_agent.current_run_id
    )

    # ========================================================
    # SIMULATED APPLICATION RESTART
    # ========================================================

    second_database = Database(
        db_path
    )

    second_run_repository = AgentRunRepository(
        second_database
    )

    ticket_repository = TicketRepository(
        second_database
    )

    ticket_service = PersistentTicketService(
        ticket_repository
    )

    second_agent = ControlledOrderAgent(
        RuleBasedPlanner(),
        run_repository=second_run_repository,
        ticket_service=ticket_service,
    )

    restored = second_agent.load_run(
        run_id
    )

    assert restored is not None
    assert restored.order_id == "8452"
    assert restored.days_delayed == 5
    assert restored.awaiting_approval is True
    assert restored.finished is False

    assert (
        second_agent.current_run_id
        == run_id
    )

    # ========================================================
    # RESUME AFTER RESTART
    # ========================================================

    finished = (
        second_agent.resume_with_approval(
            restored,
            approved=True,
        )
    )

    assert finished.finished is True
    assert finished.awaiting_approval is False
    assert finished.human_approved is True

    assert (
        finished.ticket_id
        == "TCK-1001"
    )

    # ========================================================
    # VERIFY SAME RUN WAS UPDATED
    # ========================================================

    assert (
        second_agent.current_run_id
        == run_id
    )

    persisted = (
        second_run_repository.get(
            run_id
        )
    )

    assert persisted is not None

    assert persisted.finished is True
    assert persisted.awaiting_approval is False
    assert persisted.human_approved is True

    assert (
        persisted.ticket_id
        == "TCK-1001"
    )

    # Ticket must also exist
    # in persistent storage.
    assert ticket_repository.count() == 1


def test_each_new_conversation_gets_new_run_id(
    tmp_path,
):
    database = Database(
        tmp_path / "multiple-runs.db"
    )
    database.initialize()

    repository = AgentRunRepository(
        database
    )

    agent = ControlledOrderAgent(
        RuleBasedPlanner(),
        run_repository=repository,
    )

    # ========================================================
    # FIRST RUN
    # ========================================================

    first_state = agent.run(
        "Check order 45821."
    )

    assert first_state.finished is True

    first_run_id = (
        agent.current_run_id
    )

    assert first_run_id is not None

    # ========================================================
    # SECOND RUN
    # ========================================================

    second_state = agent.run(
        "Check order 7301."
    )

    assert second_state.finished is True

    second_run_id = (
        agent.current_run_id
    )

    assert second_run_id is not None

    # Every new conversation must
    # receive a unique run identifier.
    assert (
        first_run_id
        != second_run_id
    )

    # Both runs must still exist
    # in persistent storage.
    first_persisted = repository.get(
        first_run_id
    )

    second_persisted = repository.get(
        second_run_id
    )

    assert first_persisted is not None
    assert second_persisted is not None

    assert (
        first_persisted.order_id
        == "45821"
    )

    assert (
        second_persisted.order_id
        == "7301"
    )