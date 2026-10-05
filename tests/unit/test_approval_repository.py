import pytest

from controlled_agent.domain.state import AgentState
from controlled_agent.persistence import (
    AgentRunRepository,
    ApprovalRepository,
    Database,
)


ORDER_ID = "8452"

CONTEXT_A = "a" * 64
CONTEXT_B = "b" * 64
CONTEXT_C = "c" * 64


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


def create_pending(
    repository: ApprovalRepository,
    *,
    run_id: str,
    action: str = "create_ticket",
    order_id: str = ORDER_ID,
    context_hash: str = CONTEXT_A,
) -> dict:
    return repository.create_request(
        run_id=run_id,
        action=action,
        order_id=order_id,
        context_hash=context_hash,
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

    approval = create_pending(
        repository,
        run_id=run_id,
    )

    assert approval["approval_id"]

    assert (
        approval["run_id"]
        == run_id
    )

    assert (
        approval["action"]
        == "create_ticket"
    )

    assert (
        approval["order_id"]
        == ORDER_ID
    )

    assert (
        approval["context_hash"]
        == CONTEXT_A
    )

    assert approval["approved"] is None

    assert (
        approval["status"]
        == "pending"
    )

    assert (
        approval["requested_at"]
        is not None
    )

    assert (
        approval["decided_at"]
        is None
    )

    assert (
        approval["consumed_at"]
        is None
    )


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

    pending = create_pending(
        repository,
        run_id=run_id,
    )

    decided = repository.decide(
        pending["approval_id"],
        approved=True,
    )

    assert (
        decided["approved"]
        is True
    )

    assert (
        decided["status"]
        == "approved"
    )

    assert (
        decided["decided_at"]
        is not None
    )

    assert (
        decided["consumed_at"]
        is None
    )


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

    pending = create_pending(
        repository,
        run_id=run_id,
    )

    decided = repository.decide(
        pending["approval_id"],
        approved=False,
    )

    assert (
        decided["approved"]
        is False
    )

    assert (
        decided["status"]
        == "denied"
    )

    assert (
        decided["decided_at"]
        is not None
    )

    assert (
        decided["consumed_at"]
        is None
    )


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

    pending = create_pending(
        repository,
        run_id=run_id,
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

    assert (
        stored["approved"]
        is True
    )


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

    first = create_pending(
        repository,
        run_id=run_id,
        action="other_action",
        context_hash=CONTEXT_B,
    )

    second = create_pending(
        repository,
        run_id=run_id,
        action="create_ticket",
        context_hash=CONTEXT_A,
    )

    latest = (
        repository.get_latest_pending(
            run_id,
            action="create_ticket",
            order_id=ORDER_ID,
            context_hash=CONTEXT_A,
        )
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


def test_pending_lookup_is_bound_to_context(
    tmp_path,
):
    database = Database(
        tmp_path / "context.db"
    )
    database.initialize()

    run_id = create_run(
        database
    )

    repository = ApprovalRepository(
        database
    )

    pending = create_pending(
        repository,
        run_id=run_id,
        context_hash=CONTEXT_A,
    )

    matching = (
        repository.get_latest_pending(
            run_id,
            action="create_ticket",
            order_id=ORDER_ID,
            context_hash=CONTEXT_A,
        )
    )

    mismatched = (
        repository.get_latest_pending(
            run_id,
            action="create_ticket",
            order_id=ORDER_ID,
            context_hash=CONTEXT_B,
        )
    )

    assert matching is not None

    assert (
        matching["approval_id"]
        == pending["approval_id"]
    )

    assert mismatched is None


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

    create_pending(
        repository,
        run_id=first_run_id,
        action="create_ticket",
        context_hash=CONTEXT_A,
    )

    create_pending(
        repository,
        run_id=first_run_id,
        action="another_action",
        context_hash=CONTEXT_B,
    )

    create_pending(
        repository,
        run_id=second_run_id,
        action="create_ticket",
        context_hash=CONTEXT_C,
    )

    first_history = (
        repository.get_for_run(
            first_run_id
        )
    )

    second_history = (
        repository.get_for_run(
            second_run_id
        )
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


def test_approved_request_can_be_consumed(
    tmp_path,
):
    database = Database(
        tmp_path / "consume.db"
    )
    database.initialize()

    run_id = create_run(
        database
    )

    repository = ApprovalRepository(
        database
    )

    pending = create_pending(
        repository,
        run_id=run_id,
    )

    repository.decide(
        pending["approval_id"],
        approved=True,
    )

    consumed = repository.consume(
        pending["approval_id"],
        run_id=run_id,
        action="create_ticket",
        order_id=ORDER_ID,
        context_hash=CONTEXT_A,
    )

    assert (
        consumed["approved"]
        is True
    )

    assert (
        consumed["status"]
        == "consumed"
    )

    assert (
        consumed["consumed_at"]
        is not None
    )


def test_approval_cannot_be_consumed_twice(
    tmp_path,
):
    database = Database(
        tmp_path / "replay.db"
    )
    database.initialize()

    run_id = create_run(
        database
    )

    repository = ApprovalRepository(
        database
    )

    pending = create_pending(
        repository,
        run_id=run_id,
    )

    repository.decide(
        pending["approval_id"],
        approved=True,
    )

    repository.consume(
        pending["approval_id"],
        run_id=run_id,
        action="create_ticket",
        order_id=ORDER_ID,
        context_hash=CONTEXT_A,
    )

    with pytest.raises(
        ValueError,
        match="already been consumed",
    ):
        repository.consume(
            pending["approval_id"],
            run_id=run_id,
            action="create_ticket",
            order_id=ORDER_ID,
            context_hash=CONTEXT_A,
        )


def test_approval_cannot_authorize_different_context(
    tmp_path,
):
    database = Database(
        tmp_path / "wrong-context.db"
    )
    database.initialize()

    run_id = create_run(
        database
    )

    repository = ApprovalRepository(
        database
    )

    pending = create_pending(
        repository,
        run_id=run_id,
        context_hash=CONTEXT_A,
    )

    repository.decide(
        pending["approval_id"],
        approved=True,
    )

    with pytest.raises(
        ValueError,
        match="context does not match",
    ):
        repository.consume(
            pending["approval_id"],
            run_id=run_id,
            action="create_ticket",
            order_id=ORDER_ID,
            context_hash=CONTEXT_B,
        )

    stored = repository.get(
        pending["approval_id"]
    )

    assert stored is not None

    assert (
        stored["consumed_at"]
        is None
    )


def test_denied_approval_cannot_be_consumed(
    tmp_path,
):
    database = Database(
        tmp_path / "denied-consume.db"
    )
    database.initialize()

    run_id = create_run(
        database
    )

    repository = ApprovalRepository(
        database
    )

    pending = create_pending(
        repository,
        run_id=run_id,
    )

    repository.decide(
        pending["approval_id"],
        approved=False,
    )

    with pytest.raises(
        ValueError,
        match="not approved",
    ):
        repository.consume(
            pending["approval_id"],
            run_id=run_id,
            action="create_ticket",
            order_id=ORDER_ID,
            context_hash=CONTEXT_A,
        )


def test_invalid_context_hash_is_rejected(
    tmp_path,
):
    database = Database(
        tmp_path / "invalid-hash.db"
    )
    database.initialize()

    run_id = create_run(
        database
    )

    repository = ApprovalRepository(
        database
    )

    with pytest.raises(
        ValueError,
        match="SHA-256",
    ):
        repository.create_request(
            run_id=run_id,
            action="create_ticket",
            order_id=ORDER_ID,
            context_hash="not-a-valid-hash",
        )