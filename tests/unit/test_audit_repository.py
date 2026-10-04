from controlled_agent.domain.state import AgentState
from controlled_agent.observability import AuditEvent
from controlled_agent.persistence import (
    AgentRunRepository,
    AuditRepository,
    Database,
)


def create_repositories(tmp_path):
    database = Database(
        tmp_path / "audit.db"
    )
    database.initialize()

    run_repository = AgentRunRepository(
        database
    )
    audit_repository = AuditRepository(
        database
    )

    run_id = run_repository.save(
        AgentState(
            user_message="Check order 8452"
        )
    )

    return audit_repository, run_id


def test_audit_event_can_be_persisted(
    tmp_path,
):
    repository, run_id = create_repositories(
        tmp_path
    )

    event = AuditEvent(
        timestamp="2026-10-05T00:00:00+00:00",
        step=1,
        event="planner_decision",
        detail="action=lookup_order",
    )

    event_id = repository.add(
        event,
        run_id=run_id,
    )

    assert event_id > 0
    assert repository.count_for_run(run_id) == 1


def test_audit_events_are_restored_in_order(
    tmp_path,
):
    repository, run_id = create_repositories(
        tmp_path
    )

    first = AuditEvent(
        timestamp="2026-10-05T00:00:00+00:00",
        step=1,
        event="planner_decision",
        detail="action=lookup_order",
    )

    second = AuditEvent(
        timestamp="2026-10-05T00:00:01+00:00",
        step=2,
        event="tool_output_validated",
        detail="status=delayed",
    )

    repository.add(
        first,
        run_id=run_id,
    )
    repository.add(
        second,
        run_id=run_id,
    )

    events = repository.get_for_run(
        run_id
    )

    assert len(events) == 2

    assert events[0] == first
    assert events[1] == second


def test_audit_events_are_isolated_by_run(
    tmp_path,
):
    database = Database(
        tmp_path / "audit.db"
    )
    database.initialize()

    run_repository = AgentRunRepository(
        database
    )
    repository = AuditRepository(
        database
    )

    first_run = run_repository.save(
        AgentState(
            user_message="First run"
        )
    )

    second_run = run_repository.save(
        AgentState(
            user_message="Second run"
        )
    )

    event = AuditEvent(
        timestamp="2026-10-05T00:00:00+00:00",
        step=0,
        event="request_received",
        detail="New user request received.",
    )

    repository.add(
        event,
        run_id=first_run,
    )

    assert repository.count_for_run(
        first_run
    ) == 1

    assert repository.count_for_run(
        second_run
    ) == 0


def test_audit_events_can_be_cleared_for_run(
    tmp_path,
):
    repository, run_id = create_repositories(
        tmp_path
    )

    repository.add(
        AuditEvent(
            timestamp="2026-10-05T00:00:00+00:00",
            step=0,
            event="request_received",
            detail="Test event",
        ),
        run_id=run_id,
    )

    assert repository.count_for_run(
        run_id
    ) == 1

    repository.clear_for_run(
        run_id
    )

    assert repository.count_for_run(
        run_id
    ) == 0