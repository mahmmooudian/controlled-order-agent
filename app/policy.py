"""
Backward-compatible policy imports for the v1 application.

Canonical policy implementation:
controlled_agent.policy
"""

from controlled_agent.policy import (
    ALLOWED_TOOLS,
    MAX_STEPS,
    PolicyDecision,
    can_continue_execution,
    can_offer_ticket,
    evaluate_create_ticket_policy,
    evaluate_tool_policy,
    get_tool_permission,
    is_tool_allowed,
)

__all__ = [
    "ALLOWED_TOOLS",
    "MAX_STEPS",
    "PolicyDecision",
    "can_continue_execution",
    "can_offer_ticket",
    "evaluate_create_ticket_policy",
    "evaluate_tool_policy",
    "get_tool_permission",
    "is_tool_allowed",
]
