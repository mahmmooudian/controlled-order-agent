from __future__ import annotations

from typing import Any

import pytest

from controlled_agent.services.order import (
    OrderService,
    OrderServiceTimeoutError,
)
from controlled_agent.services.ticket import (
    TicketService,
    TicketServiceError,
)
from controlled_agent.tools.order import (
    LookupOrderTimeoutError,
    LookupOrderToolError,
    lookup_order,
    lookup_order_with_retry,
)
from controlled_agent.tools.ticket import (
    CreateTicketToolError,
    create_ticket,
)


class AlwaysTimeoutOrderService(OrderService):
    """Order provider that always times out."""

    def get_order(
        self,
        order_id: str,
    ) -> dict[str, Any]:
        raise OrderServiceTimeoutError(
            "Permanent order service timeout."
        )


class NonDictionaryOrderService(OrderService):
    """Returns a malformed non-dictionary payload."""

    def get_order(
        self,
        order_id: str,
    ) -> dict[str, Any]:
        return "invalid-output"  # type: ignore[return-value]


class InvalidStatusOrderService(OrderService):
    """Returns structurally valid data with an invalid status."""

    def get_order(
        self,
        order_id: str,
    ) -> dict[str, Any]:
        return {
            "order_id": order_id,
            "status": "hacked-status",
            "days_delayed": 5,
        }


class MissingFieldOrderService(OrderService):
    """Returns an incomplete order payload."""

    def get_order(
        self,
        order_id: str,
    ) -> dict[str, Any]:
        return {
            "order_id": order_id,
            "status": "delayed",
        }


class FailingTicketService(TicketService):
    """Ticket provider that reports a service failure."""

    def create_ticket(
        self,
        *,
        order_id: str,
        reason: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        raise TicketServiceError(
            "Ticket backend unavailable."
        )


class MalformedTicketService(TicketService):
    """Returns an invalid ticket response."""

    def create_ticket(
        self,
        *,
        order_id: str,
        reason: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return {
            "status": "created",
        }


class InvalidTicketStatusService(TicketService):
    """Returns a ticket with an unsupported status."""

    def create_ticket(
        self,
        *,
        order_id: str,
        reason: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return {
            "ticket_id": "TCK-9999",
            "status": "corrupted",
        }


def test_lookup_rejects_non_dictionary_service_output():
    with pytest.raises(
        LookupOrderToolError
    ):
        lookup_order(
            "8452",
            service=NonDictionaryOrderService(),
        )


def test_lookup_rejects_invalid_order_status():
    with pytest.raises(
        LookupOrderToolError
    ):
        lookup_order(
            "8452",
            service=InvalidStatusOrderService(),
        )


def test_lookup_rejects_missing_required_fields():
    with pytest.raises(
        LookupOrderToolError
    ):
        lookup_order(
            "8452",
            service=MissingFieldOrderService(),
        )


def test_lookup_converts_service_timeout_to_tool_timeout():
    with pytest.raises(
        LookupOrderTimeoutError
    ):
        lookup_order(
            "8452",
            service=AlwaysTimeoutOrderService(),
        )


def test_lookup_retry_stops_after_retry_limit(
    capsys,
):
    with pytest.raises(
        LookupOrderTimeoutError
    ):
        lookup_order_with_retry(
            "8452",
            service=AlwaysTimeoutOrderService(),
        )

    captured = capsys.readouterr()

    assert "attempt 1" in captured.out
    assert "Retrying once" in captured.out
    assert "attempt 2" in captured.out
    assert "Retry limit reached" in captured.out


def test_ticket_service_error_becomes_tool_error():
    with pytest.raises(
        CreateTicketToolError
    ):
        create_ticket(
            order_id="8452",
            reason="Order delayed 5 days",
            idempotency_key="error-test",
            service=FailingTicketService(),
        )


def test_ticket_rejects_malformed_service_output():
    with pytest.raises(
        CreateTicketToolError
    ):
        create_ticket(
            order_id="8452",
            reason="Order delayed 5 days",
            idempotency_key="malformed-test",
            service=MalformedTicketService(),
        )


def test_ticket_rejects_invalid_service_status():
    with pytest.raises(
        CreateTicketToolError
    ):
        create_ticket(
            order_id="8452",
            reason="Order delayed 5 days",
            idempotency_key="status-test",
            service=InvalidTicketStatusService(),
        )