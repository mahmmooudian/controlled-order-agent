from __future__ import annotations

from controlled_agent.adapters.mock import (
    MockTicketService,
    TICKET_STORE,
)
from controlled_agent.domain.schemas import (
    CreateTicketInput,
    CreateTicketOutput,
)
from controlled_agent.services.ticket import (
    TicketService,
    TicketServiceError,
)


class CreateTicketToolError(Exception):
    """Base error for create_ticket."""


def create_ticket(
    order_id: str,
    reason: str,
    idempotency_key: str,
    *,
    service: TicketService | None = None,
) -> CreateTicketOutput:
    """
    WRITE tool for creating a support ticket.

    The Policy Layer must authorize this tool
    before execution.

    Flow:
    1. Validate structured input.
    2. Call TicketService.
    3. Validate structured output.
    4. Return safe result.
    """

    validated_input = CreateTicketInput(
        order_id=order_id,
        reason=reason,
        idempotency_key=idempotency_key,
    )

    selected_service = (
        service
        if service is not None
        else MockTicketService()
    )

    try:
        raw_output = selected_service.create_ticket(
            order_id=validated_input.order_id,
            reason=validated_input.reason,
            idempotency_key=validated_input.idempotency_key,
        )

    except TicketServiceError as exc:
        raise CreateTicketToolError(
            str(exc)
        ) from exc

    try:
        return CreateTicketOutput.model_validate(
            raw_output
        )

    except Exception as exc:
        raise CreateTicketToolError(
            "Invalid output returned by ticket service: "
            + str(exc)
        ) from exc