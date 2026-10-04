from controlled_agent.adapters.sqlite import (
    PersistentAuditLogger,
)
from controlled_agent.persistence import (
    AgentRunRepository,
    AuditRepository,
    Database,
)
from controlled_agent.planners import RuleBasedPlanner
from controlled_agent.runtime import ControlledOrderAgent


def create_persistent_agent(
    db_path,
):
    database = Database(
        db_path
    )
    database.initialize()

    run_repository = AgentRunRepository(
        database
    )

    audit_repository = AuditRepository(
        database
    )

    audit_logger = PersistentAuditLogger(
        audit_repository
    )

    agent = ControlledOrderAgent(
        RuleBasedPlanner(),
        audit_logger=audit_logger,
        run_repository=run_repository,
    )

    return (
        agent,
        run_repository,
        audit_repository,
    )


def test_runtime_persists_audit_events_under_run_id(
    tmp_path,
):
    (
        agent,
        _,
        audit_repository,
    ) = create_persistent_agent(
        tmp_path / "audit-runtime.db"
    )

    state = agent.run(
        "Check order 45821."
    )

    assert state.finished is True
    assert agent.current_run_id is not None

    events = audit_repository.get_for_run(
        agent.current_run_id
    )

    event_names = [
        item.event
        for item in events
    ]

    assert "request_received" in event_names
    assert "planner_decision" in event_names
    assert "policy_check" in event_names
    assert "final_response" in event_names


def test_restored_run_continues_same_audit_history(
    tmp_path,
):
    db_path = (
        tmp_path
        / "audit-restart.db"
    )

    (
        first_agent,
        _,
        first_audit_repository,
    ) = create_persistent_agent(
        db_path
    )

    state = first_agent.run(
        "Check order 8452."
    )

    assert state.awaiting_approval is True
    assert first_agent.current_run_id is not None

    run_id = first_agent.current_run_id

    initial_count = (
        first_audit_repository.count_for_run(
            run_id
        )
    )

    # Simulate application restart.
    (
        second_agent,
        _,
        second_audit_repository,
    ) = create_persistent_agent(
        db_path
    )

    restored = second_agent.load_run(
        run_id
    )

    assert restored is not None

    finished = (
        second_agent.resume_with_approval(
            restored,
            approved=False,
        )
    )

    assert finished.finished is True

    final_count = (
        second_audit_repository.count_for_run(
            run_id
        )
    )

    assert final_count > initial_count

    events = (
        second_audit_repository.get_for_run(
            run_id
        )
    )

    event_names = [
        item.event
        for item in events
    ]

    assert "approval_requested" in event_names
    assert "approval_received" in event_names


def test_new_conversations_have_isolated_audit_trails(
    tmp_path,
):
    (
        agent,
        _,
        audit_repository,
    ) = create_persistent_agent(
        tmp_path / "isolated-audit.db"
    )

    agent.run(
        "Check order 45821."
    )

    first_run_id = (
        agent.current_run_id
    )

    assert first_run_id is not None

    first_count = (
        audit_repository.count_for_run(
            first_run_id
        )
    )

    agent.run(
        "Check order 7301."
    )

    second_run_id = (
        agent.current_run_id
    )

    assert second_run_id is not None
    assert first_run_id != second_run_id

    second_count = (
        audit_repository.count_for_run(
            second_run_id
        )
    )

    assert first_count > 0
    assert second_count > 0

    # Starting the second run must not modify
    # the persistent history of the first run.
    assert (
        audit_repository.count_for_run(
            first_run_id
        )
        == first_count
    )