from controlled_agent.domain.schemas import OrderStatus
from controlled_agent.domain.state import (
    AgentState,
    AgentStatus,
)
from controlled_agent.persistence import (
    AgentRunRepository,
    Database,
)


def create_repository(tmp_path):
    database = Database(
        tmp_path / "agent.db"
    )

    database.initialize()

    return AgentRunRepository(
        database
    )


def test_agent_run_can_be_saved_and_loaded(
    tmp_path,
):
    repository = create_repository(
        tmp_path
    )

    state = AgentState(
        user_message="Check order 8452",
        latest_user_message="Check order 8452",
        order_id="8452",
        order_status=OrderStatus.DELAYED,
        days_delayed=5,
        awaiting_approval=True,
        human_approved=None,
        steps=2,
        status=AgentStatus.WAITING_FOR_APPROVAL,
        finished=False,
        final_message="Approval required.",
    )

    run_id = repository.save(
        state
    )

    loaded = repository.get(
        run_id
    )

    assert loaded is not None

    assert (
        loaded.model_dump()
        == state.model_dump()
    )


def test_agent_run_generates_unique_id(
    tmp_path,
):
    repository = create_repository(
        tmp_path
    )

    first_id = repository.save(
        AgentState(
            user_message="first"
        )
    )

    second_id = repository.save(
        AgentState(
            user_message="second"
        )
    )

    assert first_id != second_id


def test_existing_agent_run_can_be_updated(
    tmp_path,
):
    repository = create_repository(
        tmp_path
    )

    state = AgentState(
        user_message="Check order 8452"
    )

    run_id = repository.save(
        state,
        run_id="run-001",
    )

    state.order_id = "8452"
    state.order_status = OrderStatus.DELAYED
    state.days_delayed = 5
    state.awaiting_approval = True
    state.steps = 2
    state.status = (
        AgentStatus.WAITING_FOR_APPROVAL
    )
    state.final_message = (
        "Approval required."
    )

    updated_id = repository.save(
        state,
        run_id=run_id,
    )

    loaded = repository.get(
        run_id
    )

    assert updated_id == run_id
    assert loaded is not None

    assert loaded.order_id == "8452"
    assert loaded.order_status == OrderStatus.DELAYED
    assert loaded.days_delayed == 5
    assert loaded.awaiting_approval is True
    assert loaded.steps == 2
    assert (
        loaded.status
        == AgentStatus.WAITING_FOR_APPROVAL
    )


def test_unknown_agent_run_returns_none(
    tmp_path,
):
    repository = create_repository(
        tmp_path
    )

    result = repository.get(
        "missing-run"
    )

    assert result is None