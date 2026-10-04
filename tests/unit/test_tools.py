from controlled_agent.domain.schemas import OrderStatus
from controlled_agent.tools import (
    TICKET_STORE,
    create_ticket,
    lookup_order,
    lookup_order_with_retry,
)


def test_lookup_known_order():
    result = lookup_order("8452")

    assert result.order_id == "8452"
    assert result.status == OrderStatus.DELAYED
    assert result.days_delayed == 5


def test_lookup_unknown_order():
    result = lookup_order("9999")

    assert result.order_id == "9999"
    assert result.status == OrderStatus.NOT_FOUND
    assert result.days_delayed == 0


def test_lookup_discards_prompt_injection(capsys):
    result = lookup_order(
        "45821",
        simulate_injection=True,
    )

    captured = capsys.readouterr()

    assert result.order_id == "45821"
    assert result.status == OrderStatus.SHIPPED

    assert (
        "Discarded untrusted fields"
        in captured.out
    )

    assert "note" in captured.out


def test_lookup_retry_recovers_from_first_timeout(capsys):
    result = lookup_order_with_retry(
        "45821",
        simulate_timeout=True,
    )

    captured = capsys.readouterr()

    assert result.order_id == "45821"
    assert result.status == OrderStatus.SHIPPED

    assert "attempt 1" in captured.out
    assert "[TIMEOUT]" in captured.out
    assert "Retrying once" in captured.out
    assert "attempt 2" in captured.out


def test_create_ticket_creates_new_ticket():
    result = create_ticket(
        order_id="8452",
        reason="Order delayed 5 days",
        idempotency_key="unit-test-1",
    )

    assert result.status == "created"
    assert result.ticket_id == "TCK-1001"

    assert "unit-test-1" in TICKET_STORE


def test_create_ticket_is_idempotent():
    first = create_ticket(
        order_id="8452",
        reason="Order delayed 5 days",
        idempotency_key="same-request",
    )

    second = create_ticket(
        order_id="8452",
        reason="Order delayed 5 days",
        idempotency_key="same-request",
    )

    assert first.status == "created"
    assert second.status == "existing"

    assert first.ticket_id == second.ticket_id

    assert len(TICKET_STORE) == 1


def test_different_idempotency_keys_create_different_tickets():
    first = create_ticket(
        order_id="8452",
        reason="First request",
        idempotency_key="request-a",
    )

    second = create_ticket(
        order_id="8452",
        reason="Second request",
        idempotency_key="request-b",
    )

    assert first.ticket_id == "TCK-1001"
    assert second.ticket_id == "TCK-1002"

    assert len(TICKET_STORE) == 2