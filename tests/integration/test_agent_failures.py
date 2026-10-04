from controlled_agent.domain.schemas import (
    AgentAction,
    AgentDecision,
    OrderStatus,
)
from controlled_agent.domain.state import (
    AgentState,
    AgentStatus,
)
from controlled_agent.planners import (
    BasePlanner,
    RuleBasedPlanner,
)
from controlled_agent.runtime import ControlledOrderAgent


class UnsafePlanner(BasePlanner):
    """
    Deliberately attempts a WRITE action
    without human approval.
    """

    def decide(
        self,
        state: AgentState,
    ) -> AgentDecision:

        if state.order_status is None:
            return AgentDecision(
                action=AgentAction.LOOKUP_ORDER,
                order_id="8452",
            )

        return AgentDecision(
            action=AgentAction.CREATE_TICKET,
            order_id="8452",
        )


def test_human_denial_does_not_create_ticket():
    agent = ControlledOrderAgent(
        RuleBasedPlanner()
    )

    state = agent.run(
        "Check order 8452."
    )

    assert state.status == AgentStatus.WAITING_FOR_APPROVAL
    assert state.awaiting_approval is True
    assert state.ticket_id is None

    state = agent.resume_with_approval(
        state,
        approved=False,
    )

    assert state.human_approved is False
    assert state.ticket_id is None
    assert state.finished is True

    events = [
        event.event
        for event in agent.audit.get_events()
    ]

    assert "approval_received" in events
    assert "ticket_created" not in events


def test_small_delay_does_not_create_ticket():
    agent = ControlledOrderAgent(
        RuleBasedPlanner()
    )

    state = agent.run(
        "Check order 45821."
    )

    assert state.status == AgentStatus.DONE
    assert state.order_id == "45821"
    assert state.order_status == OrderStatus.SHIPPED
    assert state.days_delayed == 2
    assert state.ticket_id is None
    assert state.finished is True


def test_unknown_order_returns_not_found_without_ticket():
    agent = ControlledOrderAgent(
        RuleBasedPlanner()
    )

    state = agent.run(
        "Check order 9999."
    )

    assert state.status == AgentStatus.DONE
    assert state.order_id == "9999"
    assert state.order_status == OrderStatus.NOT_FOUND
    assert state.days_delayed == 0
    assert state.ticket_id is None
    assert state.finished is True


def test_policy_blocks_unsafe_write_without_approval():
    agent = ControlledOrderAgent(
        UnsafePlanner()
    )

    state = agent.run(
        "Create a ticket for order 8452."
    )

    assert state.status == AgentStatus.FAILED
    assert state.order_id == "8452"
    assert state.days_delayed == 5
    assert state.human_approved is None
    assert state.ticket_id is None
    assert state.finished is True

    events = [
        event.event
        for event in agent.audit.get_events()
    ]

    assert "write_blocked" in events
    assert "ticket_created" not in events