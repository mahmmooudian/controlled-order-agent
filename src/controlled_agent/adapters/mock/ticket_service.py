from __future__ import annotations

from typing import Any

from controlled_agent.services.ticket import TicketService


TICKET_STORE: dict[str, dict[str, Any]] = {}


class MockTicketService(TicketService):
    """
    In-memory ticket provider for development
    and offline testing.

    Idempotency is enforced through the
    idempotency_key.
    """

    def create_ticket(
        self,
        *,
        order_id: str,
        reason: str,
        idempotency_key: str,
    ) -> dict[str, Any]:

        existing_ticket = TICKET_STORE.get(
            idempotency_key
        )

        if existing_ticket is not None:

            print(
                "[IDEMPOTENCY] Existing ticket returned:",
                existing_ticket["ticket_id"],
            )

            return {
                "ticket_id":
                    existing_ticket["ticket_id"],
                "status": "existing",
            }

        ticket_number = (
            len(TICKET_STORE) + 1001
        )

        ticket_id = (
            f"TCK-{ticket_number}"
        )

        new_ticket = {
            "ticket_id": ticket_id,
            "order_id": order_id,
            "reason": reason,
            "idempotency_key":
                idempotency_key,
        }

        TICKET_STORE[
            idempotency_key
        ] = new_ticket

        print(
            "[WRITE] Ticket created:",
            ticket_id,
        )

        return {
            "ticket_id": ticket_id,
            "status": "created",
        }
