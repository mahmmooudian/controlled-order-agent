from controlled_agent.adapters.sqlite import (
    PersistentAuditLogger,
)
from controlled_agent.domain.state import AgentState
from controlled_agent.persistence import (
    AgentRunRepository,
    AuditRepository,
    Database,
)


def create_logger(tmp_path):
    database = Database(
        tmp_path / "audit.db"
    )
    database.initialize()

    run_repository = AgentRunRepository(
        database
    )

    run_id = run_repository.save(
        AgentState(
            user_message="Check order 8452"
        )
    )

    audit_repository = AuditRepository(
        database
    )

    logger = PersistentAuditLogger(
        audit_repository,
        run_id=run_id,
    )

    return (
        logger,
        audit_repository,
        run_id,
        run_repository,
    )


def test_persistent_logger_keeps_in_memory_event(
    tmp_path,
):
    (
        logger,
        repository,
        run_id,
        _,
    ) = create_logger(tmp_path)

    logger.log(
        step=1,
        event="planner_decision",
        detail="action=lookup_order",
    )

    events = logger.get_events()

    assert len(events) == 1
    assert events[0].event == "planner_decision"

    assert repository.count_for_run(
        run_id
    ) == 1


def test_persistent_logger_stores_event_in_database(
    tmp_path,
):
    (
        logger,
        repository,
        run_id,
        _,
    ) = create_logger(tmp_path)

    logger.log(
        step=2,
        event="tool_output_validated",
        detail="status=delayed",
    )

    stored = repository.get_for_run(
        run_id
    )

    assert len(stored) == 1
    assert stored[0].step == 2
    assert (
        stored[0].event
        == "tool_output_validated"
    )
    assert (
        stored[0].detail
        == "status=delayed"
    )


def test_clear_only_clears_memory_not_history(
    tmp_path,
):
    (
        logger,
        repository,
        run_id,
        _,
    ) = create_logger(tmp_path)

    logger.log(
        step=0,
        event="request_received",
        detail="New request",
    )

    logger.clear()

    assert logger.get_events() == []

    # Persistent audit history must survive.
    assert repository.count_for_run(
        run_id
    ) == 1


def test_logger_can_switch_to_another_run(
    tmp_path,
):
    (
        logger,
        repository,
        first_run,
        run_repository,
    ) = create_logger(tmp_path)

    logger.log(
        step=0,
        event="request_received",
        detail="First run",
    )

    second_run = run_repository.save(
        AgentState(
            user_message="Second request"
        )
    )

    logger.set_run_id(
        second_run
    )

    logger.log(
        step=0,
        event="request_received",
        detail="Second run",
    )

    assert repository.count_for_run(
        first_run
    ) == 1

    assert repository.count_for_run(
        second_run
    ) == 1


def test_persisted_history_requires_explicit_clear(
    tmp_path,
):
    (
        logger,
        repository,
        run_id,
        _,
    ) = create_logger(tmp_path)

    logger.log(
        step=1,
        event="test_event",
        detail="Persistent event",
    )

    assert repository.count_for_run(
        run_id
    ) == 1

    logger.clear_persisted()

    assert repository.count_for_run(
        run_id
    ) == 0