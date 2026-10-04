from controlled_agent.domain.state import AgentStatus
from controlled_agent.planners import RuleBasedPlanner
from controlled_agent.runtime import ControlledOrderAgent


def test_delayed_order_requires_approval_and_creates_ticket():
    agent = ControlledOrderAgent(
        planner=RuleBasedPlanner()
    )

    state = agent.run(
        "Check order 8452 and create a support ticket if needed."
    )

    # Before human approval, no WRITE action may occur.
    assert state.status == AgentStatus.WAITING_FOR_APPROVAL
    assert state.order_id == "8452"
    assert state.days_delayed == 5
    assert state.awaiting_approval is True
    assert state.human_approved is None
    assert state.ticket_id is None
    assert state.finished is False

    state = agent.resume_with_approval(
        state,
        approved=True,
    )

    # After explicit approval, ticket creation is allowed.
    assert state.status == AgentStatus.DONE
    assert state.order_id == "8452"
    assert state.days_delayed == 5
    assert state.awaiting_approval is False
    assert state.human_approved is True
    assert state.ticket_id == "TCK-1001"
    assert state.finished is True

    audit_events = [
        event.event
        for event in agent.audit.get_events()
    ]

    assert "approval_requested" in audit_events
    assert "approval_received" in audit_events
    assert "create_ticket_called" in audit_events
    assert "ticket_created" in audit_events
    assert "final_response" in audit_events