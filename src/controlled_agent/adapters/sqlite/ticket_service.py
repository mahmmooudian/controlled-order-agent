from __future__ import annotations

import sqlite3
from typing import Any

from controlled_agent.persistence import TicketRepository
from controlled_agent.services.ticket import (
    TicketService,
    TicketServiceError,
)


class PersistentTicketService(TicketService):
    """
    SQLite-backed ticket service.

    Tickets and idempotency records survive
    process restarts because they are stored
    in persistent SQLite storage.
    """

    def __init__(
        self,
        repository: TicketRepository,
    ) -> None:
        self.repository = repository

    def create_ticket(
        self,
        *,
        order_id: str,
        reason: str,
        idempotency_key: str,
    ) -> dict[str, Any]:

        try:
            result = self.repository.create(
                order_id=order_id,
                reason=reason,
                idempotency_key=idempotency_key,
            )

        except sqlite3.Error as exc:
            raise TicketServiceError(
                "Persistent ticket storage failed: "
                + str(exc)
            ) from exc

        if result["status"] == "existing":
            print(
                "[IDEMPOTENCY] Existing persistent ticket returned:",
                result["ticket_id"],
            )
        else:
            print(
                "[WRITE] Persistent ticket created:",
                result["ticket_id"],
            )

        # Only expose the fields expected by CreateTicketOutput.
        return {
            "ticket_id": result["ticket_id"],
            "status": result["status"],
        }