"""
Backward-compatible ticket tool imports for the v1 application.

Canonical implementation:
controlled_agent.tools.ticket
"""

from controlled_agent.tools.ticket import (
    CreateTicketToolError,
    TICKET_STORE,
    create_ticket,
)

__all__ = [
    "CreateTicketToolError",
    "TICKET_STORE",
    "create_ticket",
]
