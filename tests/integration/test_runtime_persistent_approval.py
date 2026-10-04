from controlled_agent.adapters.sqlite import (
    PersistentTicketService,
)
from controlled_agent.domain.state import AgentStatus
from controlled_agent.persistence import (
    AgentRunRepository,
    ApprovalRepository,
    Database,
    TicketRepository,
)
from controlled_agent.planners import RuleBasedPlanner
from controlled_agent.runtime import ControlledOrderAgent


def create_persistent_agent(
    db_path,
    *,
    with_ticket_service: bool = False,
):
    database = Database(
        db_path
    )
    database.initialize()

    run_repository = AgentRunRepository(
        database
    )

    approval_repository = ApprovalRepository(
        database
    )

    ticket_repository = TicketRepository(
        database
    )

    ticket_service = None

    if with_ticket_service:
        ticket_service = PersistentTicketService(
            ticket_repository
        )

    agent = ControlledOrderAgent(
        RuleBasedPlanner(),
        run_repository=run_repository,
        approval_repository=approval_repository,
        ticket_service=ticket_service,
    )

    return (
        agent,
        run_repository,
        approval_repository,
        ticket_repository,
    )


def test_runtime_creates_pending_approval_request(
    tmp_path,
):
    (
        agent,
        _,
        approval_repository,
        _,
    ) = create_persistent_agent(
        tmp_path / "pending-approval.db"
    )

    state = agent.run(
        "Check order 8452."
    )

    assert state.awaiting_approval is True
    assert (
        state.status
        == AgentStatus.WAITING_FOR_APPROVAL
    )

    assert agent.current_run_id is not None

    approvals = (
        approval_repository.get_for_run(
            agent.current_run_id
        )
    )

    assert len(approvals) == 1

    approval = approvals[0]

    assert (
        approval["action"]
        == "create_ticket"
    )

    assert approval["approved"] is None
    assert approval["decided_at"] is None


def test_runtime_persists_human_approval(
    tmp_path,
):
    (
        agent,
        _,
        approval_repository,
        ticket_repository,
    ) = create_persistent_agent(
        tmp_path / "approved.db",
        with_ticket_service=True,
    )

    state = agent.run(
        "Check order 8452."
    )

    assert state.awaiting_approval is True
    assert agent.current_run_id is not None

    run_id = agent.current_run_id

    pending = (
        approval_repository.get_latest_pending(
            run_id,
            action="create_ticket",
        )
    )

    assert pending is not None
    assert pending["approved"] is None

    result = agent.resume_with_approval(
        state,
        approved=True,
    )

    assert result.finished is True
    assert result.human_approved is True
    assert result.awaiting_approval is False

    stored = approval_repository.get(
        pending["approval_id"]
    )

    assert stored is not None
    assert stored["approved"] is True
    assert stored["decided_at"] is not None

    assert (
        approval_repository.get_latest_pending(
            run_id,
            action="create_ticket",
        )
        is None
    )

    assert ticket_repository.count() == 1


def test_runtime_persists_human_denial(
    tmp_path,
):
    (
        agent,
        _,
        approval_repository,
        ticket_repository,
    ) = create_persistent_agent(
        tmp_path / "denied.db",
        with_ticket_service=True,
    )

    state = agent.run(
        "Check order 8452."
    )

    assert state.awaiting_approval is True
    assert agent.current_run_id is not None

    run_id = agent.current_run_id

    pending = (
        approval_repository.get_latest_pending(
            run_id,
            action="create_ticket",
        )
    )

    assert pending is not None

    result = agent.resume_with_approval(
        state,
        approved=False,
    )

    assert result.finished is True
    assert result.human_approved is False
    assert result.awaiting_approval is False

    stored = approval_repository.get(
        pending["approval_id"]
    )

    assert stored is not None
    assert stored["approved"] is False
    assert stored["decided_at"] is not None

    # A denied approval must never result
    # in a WRITE tool execution.
    assert ticket_repository.count() == 0


def test_approval_survives_agent_restart(
    tmp_path,
):
    db_path = (
        tmp_path
        / "approval-restart.db"
    )

    # ========================================================
    # FIRST AGENT INSTANCE
    # ========================================================

    (
        first_agent,
        _,
        first_approval_repository,
        _,
    ) = create_persistent_agent(
        db_path
    )

    state = first_agent.run(
        "Check order 8452."
    )

    assert state.awaiting_approval is True
    assert first_agent.current_run_id is not None

    run_id = first_agent.current_run_id

    pending = (
        first_approval_repository
        .get_latest_pending(
            run_id,
            action="create_ticket",
        )
    )

    assert pending is not None

    approval_id = (
        pending["approval_id"]
    )

    # ========================================================
    # SIMULATED APPLICATION RESTART
    # ========================================================

    (
        second_agent,
        _,
        second_approval_repository,
        second_ticket_repository,
    ) = create_persistent_agent(
        db_path,
        with_ticket_service=True,
    )

    restored = second_agent.load_run(
        run_id
    )

    assert restored is not None

    assert (
        restored.status
        == AgentStatus.WAITING_FOR_APPROVAL
    )

    result = (
        second_agent.resume_with_approval(
            restored,
            approved=True,
        )
    )

    assert result.finished is True
    assert result.human_approved is True

    stored = (
        second_approval_repository.get(
            approval_id
        )
    )

    assert stored is not None
    assert stored["approved"] is True
    assert stored["decided_at"] is not None

    assert (
        second_ticket_repository.count()
        == 1
    )


def test_runtime_fails_closed_without_pending_approval(
    tmp_path,
):
    db_path = (
        tmp_path
        / "fail-closed.db"
    )

    # ========================================================
    # CREATE A WAITING STATE WITHOUT APPROVAL PERSISTENCE
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
    assert first_agent.current_run_id is not None

    run_id = first_agent.current_run_id

    # No ApprovalRepository was connected to the first
    # runtime, so there must be no approval DB record.

    # ========================================================
    # RESTART WITH APPROVAL PERSISTENCE ENABLED
    # ========================================================

    second_database = Database(
        db_path
    )

    second_run_repository = AgentRunRepository(
        second_database
    )

    second_approval_repository = (
        ApprovalRepository(
            second_database
        )
    )

    second_ticket_repository = (
        TicketRepository(
            second_database
        )
    )

    second_ticket_service = (
        PersistentTicketService(
            second_ticket_repository
        )
    )

    second_agent = ControlledOrderAgent(
        RuleBasedPlanner(),
        run_repository=second_run_repository,
        approval_repository=(
            second_approval_repository
        ),
        ticket_service=second_ticket_service,
    )

    restored = second_agent.load_run(
        run_id
    )

    assert restored is not None
    assert restored.awaiting_approval is True

    assert (
        second_approval_repository
        .get_latest_pending(
            run_id,
            action="create_ticket",
        )
        is None
    )

    # Attempting to approve without a matching
    # persistent pending record must fail closed.
    result = (
        second_agent.resume_with_approval(
            restored,
            approved=True,
        )
    )

    assert result.finished is True

    assert (
        result.status
        == AgentStatus.FAILED
    )

    assert result.ticket_id is None

    assert (
        second_ticket_repository.count()
        == 0
    )