import pytest

from controlled_agent.domain.schemas import ToolPermission
from controlled_agent.policy import (
    MAX_STEPS,
    PolicyDecision,
    can_continue_execution,
    can_offer_ticket,
    evaluate_create_ticket_policy,
    evaluate_tool_policy,
    get_tool_permission,
    is_tool_allowed,
)


def test_known_tools_are_allowed():
    assert is_tool_allowed("lookup_order") is True
    assert is_tool_allowed("create_ticket") is True


def test_unknown_tool_is_not_allowed():
    assert is_tool_allowed("delete_database") is False


def test_tool_permissions_are_correct():
    assert (
        get_tool_permission("lookup_order")
        == ToolPermission.READ
    )
    assert (
        get_tool_permission("create_ticket")
        == ToolPermission.WRITE
    )
    assert get_tool_permission("unknown") is None


@pytest.mark.parametrize(
    ("days_delayed", "expected"),
    [
        (None, False),
        (0, False),
        (3, False),
        (4, True),
        (10, True),
    ],
)
def test_ticket_eligibility(
    days_delayed,
    expected,
):
    assert can_offer_ticket(days_delayed) is expected


def test_ticket_policy_denies_small_delay():
    result = evaluate_create_ticket_policy(
        days_delayed=3,
        human_approved=True,
    )

    assert result == PolicyDecision.DENY


def test_ticket_policy_requires_approval():
    result = evaluate_create_ticket_policy(
        days_delayed=5,
        human_approved=None,
    )

    assert result == PolicyDecision.REQUIRE_APPROVAL


def test_ticket_policy_still_requires_approval_after_denial():
    result = evaluate_create_ticket_policy(
        days_delayed=5,
        human_approved=False,
    )

    assert result == PolicyDecision.REQUIRE_APPROVAL


def test_ticket_policy_allows_explicit_approval():
    result = evaluate_create_ticket_policy(
        days_delayed=5,
        human_approved=True,
    )

    assert result == PolicyDecision.ALLOW


def test_read_tool_is_allowed():
    result = evaluate_tool_policy(
        tool_name="lookup_order"
    )

    assert result == PolicyDecision.ALLOW


def test_unknown_tool_is_denied():
    result = evaluate_tool_policy(
        tool_name="dangerous_tool"
    )

    assert result == PolicyDecision.DENY


def test_write_tool_requires_approval():
    result = evaluate_tool_policy(
        tool_name="create_ticket",
        days_delayed=5,
        human_approved=None,
    )

    assert result == PolicyDecision.REQUIRE_APPROVAL


def test_max_steps_boundary():
    assert can_continue_execution(0) is True
    assert can_continue_execution(MAX_STEPS - 1) is True
    assert can_continue_execution(MAX_STEPS) is False
    assert can_continue_execution(MAX_STEPS + 1) is False