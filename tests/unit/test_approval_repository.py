import pytest

from controlled_agent.domain.state import AgentState
from controlled_agent.persistence import (
    AgentRunRepository,
    ApprovalRepository,
    Database,
)


def create_run(
    database: Database,
) -> str:
    run_repository = AgentRunRepository(
        database
    )

    state = AgentState(
        user_message="Check order 8452.",
        latest_user_message="Check order 8452.",
    )

    return run_repository.save(
        state
    )


def test_create_pending_approval_request(
    tmp_path,
):
    database = Database(
        tmp_path / "approval.db"
    )
    database.initialize()

    run_id = create_run(
        database
    )

    repository = ApprovalRepository(
        database
    )

    approval = repository.create_request(
        run_id=run_id,
        action="create_ticket",
    )

    assert approval["approval_id"]
    assert approval["run_id"] == run_id
    assert approval["action"] == "create_ticket"

    assert approval["approved"] is None
    assert approval["requested_at"] is not None
    assert approval["decided_at"] is None


def test_approve_pending_request(
    tmp_path,
):
    database = Database(
        tmp_path / "approve.db"
    )
    database.initialize()

    run_id = create_run(
        database
    )

    repository = ApprovalRepository(
        database
    )

    pending = repository.create_request(
        run_id=run_id,
        action="create_ticket",
    )

    decided = repository.decide(
        pending["approval_id"],
        approved=True,
    )

    assert decided["approved"] is True
    assert decided["decided_at"] is not None


def test_deny_pending_request(
    tmp_path,
):
    database = Database(
        tmp_path / "deny.db"
    )
    database.initialize()

    run_id = create_run(
        database
    )

    repository = ApprovalRepository(
        database
    )

    pending = repository.create_request(
        run_id=run_id,
        action="create_ticket",
    )

    decided = repository.decide(
        pending["approval_id"],
        approved=False,
    )

    assert decided["approved"] is False
    assert decided["decided_at"] is not None


def test_decision_is_immutable(
    tmp_path,
):
    database = Database(
        tmp_path / "immutable.db"
    )
    database.initialize()

    run_id = create_run(
        database
    )

    repository = ApprovalRepository(
        database
    )

    pending = repository.create_request(
        run_id=run_id,
        action="create_ticket",
    )

    repository.decide(
        pending["approval_id"],
        approved=True,
    )

    with pytest.raises(
        ValueError,
        match="already been decided",
    ):
        repository.decide(
            pending["approval_id"],
            approved=False,
        )

    stored = repository.get(
        pending["approval_id"]
    )

    assert stored is not None
    assert stored["approved"] is True


def test_latest_pending_approval_can_be_found(
    tmp_path,
):
    database = Database(
        tmp_path / "pending.db"
    )
    database.initialize()

    run_id = create_run(
        database
    )

    repository = ApprovalRepository(
        database
    )

    first = repository.create_request(
        run_id=run_id,
        action="other_action",
    )

    second = repository.create_request(
        run_id=run_id,
        action="create_ticket",
    )

    latest = repository.get_latest_pending(
        run_id,
        action="create_ticket",
    )

    assert latest is not None

    assert (
        latest["approval_id"]
        == second["approval_id"]
    )

    assert (
        latest["approval_id"]
        != first["approval_id"]
    )


def test_approval_history_is_scoped_to_run(
    tmp_path,
):
    database = Database(
        tmp_path / "history.db"
    )
    database.initialize()

    first_run_id = create_run(
        database
    )

    second_run_id = create_run(
        database
    )

    repository = ApprovalRepository(
        database
    )

    repository.create_request(
        run_id=first_run_id,
        action="create_ticket",
    )

    repository.create_request(
        run_id=first_run_id,
        action="another_action",
    )

    repository.create_request(
        run_id=second_run_id,
        action="create_ticket",
    )

    first_history = repository.get_for_run(
        first_run_id
    )

    second_history = repository.get_for_run(
        second_run_id
    )

    assert len(first_history) == 2
    assert len(second_history) == 1

    assert (
        repository.count_for_run(
            first_run_id
        )
        == 2
    )

    assert (
        repository.count_for_run(
            second_run_id
        )
        == 1
    )