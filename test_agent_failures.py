from app.agent import ControlledOrderAgent
from app.planner import (
    BasePlanner,
    RuleBasedPlanner,
)
from app.schemas import (
    AgentAction,
    AgentDecision,
)
from app.state import AgentState


# ============================================================
# HELPER
# ============================================================

def print_result(
    title: str,
    agent: ControlledOrderAgent,
    state: AgentState,
) -> None:

    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

    print("status:", state.status)
    print("order_id:", state.order_id)
    print("days_delayed:", state.days_delayed)
    print("human_approved:", state.human_approved)
    print("ticket_id:", state.ticket_id)
    print("finished:", state.finished)
    print("message:", state.final_message)

    agent.audit.print_summary()


# ============================================================
# TEST 1
# HUMAN DENIES TICKET CREATION
# ============================================================

print("\nTEST 1 - HUMAN DENIES APPROVAL")

agent = ControlledOrderAgent(
    RuleBasedPlanner()
)

state = agent.run(
    "وضعیت سفارش 8452 را بگو."
)

if state.awaiting_approval:
    state = agent.resume_with_approval(
        state,
        approved=False,
    )

print_result(
    "RESULT - APPROVAL DENIED",
    agent,
    state,
)


# ============================================================
# TEST 2
# SMALL DELAY - NO TICKET SHOULD BE CREATED
# ============================================================

print("\nTEST 2 - SMALL DELAY")

agent = ControlledOrderAgent(
    RuleBasedPlanner()
)

state = agent.run(
    "وضعیت سفارش 45821 را بگو."
)

print_result(
    "RESULT - SMALL DELAY",
    agent,
    state,
)


# ============================================================
# TEST 3
# ORDER NOT FOUND
# ============================================================

print("\nTEST 3 - ORDER NOT FOUND")

agent = ControlledOrderAgent(
    RuleBasedPlanner()
)

state = agent.run(
    "وضعیت سفارش 9999 را بگو."
)

print_result(
    "RESULT - ORDER NOT FOUND",
    agent,
    state,
)


# ============================================================
# TEST 4
# MALICIOUS / WRONG PLANNER
#
# Planner intentionally tries to call create_ticket
# without Human Approval.
#
# Policy Layer MUST block the WRITE action.
# ============================================================

class UnsafePlanner(BasePlanner):

    def decide(
        self,
        state: AgentState,
    ) -> AgentDecision:

        # First retrieve the order
        if state.order_status is None:
            return AgentDecision(
                action=AgentAction.LOOKUP_ORDER,
                order_id="8452",
            )

        # Intentionally violate policy:
        # try to create ticket with no approval
        return AgentDecision(
            action=AgentAction.CREATE_TICKET,
            order_id="8452",
        )


print("\nTEST 4 - UNSAFE PLANNER")

agent = ControlledOrderAgent(
    UnsafePlanner()
)

state = agent.run(
    "Create a ticket for order 8452."
)

print_result(
    "RESULT - POLICY SAFETY GATE",
    agent,
    state,
)