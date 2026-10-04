from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class TicketServiceError(Exception):
    """Base exception for ticket service failures."""


class TicketService(ABC):
    """
    Contract for ticket providers.

    Implementations may use:
    - in-memory storage
    - a database
    - Zendesk
    - Freshdesk
    - Jira
    - another external API
    """

    @abstractmethod
    def create_ticket(
        self,
        *,
        order_id: str,
        reason: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """
        Create a new ticket or return an existing one.

        The service implementation is responsible
        for enforcing idempotency.
        """
        raise NotImplementedError
