from __future__ import annotations

from controlled_agent.domain.schemas import (
    CreateTicketInput,
    CreateTicketOutput,
)


# ============================================================
# MOCK TICKET DATABASE
# ============================================================

TICKET_STORE: dict[str, dict] = {}


# ============================================================
# CUSTOM TOOL ERRORS
# ============================================================

class CreateTicketToolError(Exception):
    """Base error for create_ticket."""
    pass


# ============================================================
# WRITE TOOL
# ============================================================

def create_ticket(
    order_id: str,
    reason: str,
    idempotency_key: str,
) -> CreateTicketOutput:
    """
    WRITE tool for creating a support ticket.

    Important:
    Human approval will be enforced by the Policy Layer
    before this function is allowed to run.

    Idempotency guarantees that repeating the same request
    will not create duplicate tickets.
    """

    # --------------------------------------------------------
    # STEP 1: Validate structured input
    # --------------------------------------------------------

    validated_input = CreateTicketInput(
        order_id=order_id,
        reason=reason,
        idempotency_key=idempotency_key,
    )

    # --------------------------------------------------------
    # STEP 2: Idempotency check
    # --------------------------------------------------------

    existing_ticket = TICKET_STORE.get(
        validated_input.idempotency_key
    )

    if existing_ticket is not None:

        print(
            "[IDEMPOTENCY] Existing ticket returned:",
            existing_ticket["ticket_id"],
        )

        return CreateTicketOutput(
            ticket_id=existing_ticket["ticket_id"],
            status="existing",
        )

    # --------------------------------------------------------
    # STEP 3: Create new ticket
    # --------------------------------------------------------

    ticket_number = len(TICKET_STORE) + 1001

    ticket_id = f"TCK-{ticket_number}"

    new_ticket = {
        "ticket_id": ticket_id,
        "order_id": validated_input.order_id,
        "reason": validated_input.reason,
        "idempotency_key": validated_input.idempotency_key,
    }

    # --------------------------------------------------------
    # STEP 4: Save ticket
    # --------------------------------------------------------

    TICKET_STORE[
        validated_input.idempotency_key
    ] = new_ticket

    print(
        "[WRITE] Ticket created:",
        ticket_id,
    )

    # --------------------------------------------------------
    # STEP 5: Return structured result
    # --------------------------------------------------------

    return CreateTicketOutput(
        ticket_id=ticket_id,
        status="created",
    )