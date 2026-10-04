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
from controlled_agent.policy import MAX_STEPS
from controlled_agent.runtime import ControlledOrderAgent


class LoopPlanner(BasePlanner):
    """
    Planner that never progresses beyond lookup_order.

    Used to verify MAX_STEPS protection.
    """

    def decide(
        self,
        state: AgentState,
    ) -> AgentDecision:

        return AgentDecision(
            action=AgentAction.LOOKUP_ORDER,
            order_id="8452",
        )


def test_prompt_injection_in_tool_output_is_discarded():
    agent = ControlledOrderAgent(
        RuleBasedPlanner(),
        simulate_lookup_injection=True,
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

    events = [
        event.event
        for event in agent.audit.get_events()
    ]

    assert "tool_output_validated" in events
    assert "ticket_created" not in events


def test_max_steps_prevents_infinite_agent_loop():
    agent = ControlledOrderAgent(
        LoopPlanner()
    )

    state = agent.run(
        "Check order 8452."
    )

    assert state.status == AgentStatus.ESCALATED
    assert state.steps == MAX_STEPS
    assert state.ticket_id is None
    assert state.finished is True

    events = [
        event.event
        for event in agent.audit.get_events()
    ]

    assert "max_steps_reached" in events