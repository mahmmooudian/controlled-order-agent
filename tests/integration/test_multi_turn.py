from controlled_agent.domain.state import AgentStatus
from controlled_agent.planners import RuleBasedPlanner
from controlled_agent.runtime import ControlledOrderAgent


def test_multi_turn_order_flow_with_human_approval():
    agent = ControlledOrderAgent(
        RuleBasedPlanner()
    )

    # Turn 1: missing order ID.
    state = agent.run(
        "Where is my order?"
    )

    assert state.status == AgentStatus.WAITING_FOR_INPUT
    assert state.awaiting_user_input is True
    assert state.order_id is None
    assert state.ticket_id is None
    assert state.finished is False

    # Turn 2: user provides order ID.
    state = agent.resume_with_user_input(
        state,
        "8452",
    )

    assert state.status == AgentStatus.WAITING_FOR_APPROVAL
    assert state.awaiting_user_input is False
    assert state.awaiting_approval is True
    assert state.order_id == "8452"
    assert state.days_delayed == 5
    assert state.ticket_id is None

    # Turn 3: explicit human approval.
    state = agent.resume_with_approval(
        state,
        approved=True,
    )

    assert state.status == AgentStatus.DONE
    assert state.awaiting_approval is False
    assert state.human_approved is True
    assert state.order_id == "8452"
    assert state.days_delayed == 5
    assert state.ticket_id == "TCK-1001"
    assert state.finished is True

    events = [
        event.event
        for event in agent.audit.get_events()
    ]

    assert "user_input_requested" in events
    assert "user_input_received" in events
    assert "approval_requested" in events
    assert "approval_received" in events
    assert "ticket_created" in events