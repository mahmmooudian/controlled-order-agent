from __future__ import annotations

from enum import Enum

from app.schemas import ToolPermission


# ============================================================
# GLOBAL POLICY SETTINGS
# ============================================================

MAX_STEPS = 4


ALLOWED_TOOLS: dict[str, ToolPermission] = {
    "lookup_order": ToolPermission.READ,
    "create_ticket": ToolPermission.WRITE,
}


# ============================================================
# POLICY DECISION
# ============================================================

class PolicyDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


# ============================================================
# TOOL PERMISSION CHECK
# ============================================================

def is_tool_allowed(tool_name: str) -> bool:
    """
    Check whether a tool is available to this Agent.
    """

    return tool_name in ALLOWED_TOOLS


def get_tool_permission(
    tool_name: str,
) -> ToolPermission | None:
    """
    Return READ / WRITE permission for a tool.
    """

    return ALLOWED_TOOLS.get(tool_name)


# ============================================================
# TICKET ELIGIBILITY
# ============================================================

def can_offer_ticket(
    days_delayed: int | None,
) -> bool:
    """
    A ticket may only be proposed when delay > 3 days.
    """

    if days_delayed is None:
        return False

    return days_delayed > 3


# ============================================================
# WRITE POLICY
# ============================================================

def evaluate_create_ticket_policy(
    *,
    days_delayed: int | None,
    human_approved: bool | None,
) -> PolicyDecision:
    """
    Decide whether create_ticket may run.

    Rules:
    1. If delay <= 3 -> DENY
    2. If delay > 3 and no explicit approval -> REQUIRE_APPROVAL
    3. If delay > 3 and human_approved is True -> ALLOW
    """

    if not can_offer_ticket(
        days_delayed
    ):
        return PolicyDecision.DENY

    if human_approved is not True:
        return PolicyDecision.REQUIRE_APPROVAL

    return PolicyDecision.ALLOW


# ============================================================
# GENERIC TOOL POLICY
# ============================================================

def evaluate_tool_policy(
    *,
    tool_name: str,
    days_delayed: int | None = None,
    human_approved: bool | None = None,
) -> PolicyDecision:
    """
    Central policy gate for all tool calls.
    """

    if not is_tool_allowed(tool_name):
        return PolicyDecision.DENY

    permission = get_tool_permission(
        tool_name
    )

    # READ tools are allowed once input validation passes.
    if permission == ToolPermission.READ:
        return PolicyDecision.ALLOW

    # WRITE tools need additional policy checks.
    if tool_name == "create_ticket":
        return evaluate_create_ticket_policy(
            days_delayed=days_delayed,
            human_approved=human_approved,
        )

    return PolicyDecision.DENY


# ============================================================
# MAX STEP CONTROL
# ============================================================

def can_continue_execution(
    current_step: int,
) -> bool:
    """
    Prevent infinite or excessive Agent loops.
    """

    return current_step < MAX_STEPS