from app.agent import ControlledOrderAgent
from app.planner import RuleBasedPlanner


print("=" * 70)
print("MULTI-TURN CONVERSATION TEST")
print("=" * 70)


# ============================================================
# CREATE AGENT
# ============================================================

agent = ControlledOrderAgent(
    RuleBasedPlanner()
)


# ============================================================
# TURN 1
# USER DOES NOT PROVIDE ORDER ID
# ============================================================

print("\nUSER:")
print("سفارش من کجاست؟")

state = agent.run(
    "سفارش من کجاست؟"
)

print("\nAGENT:")
print(state.final_message)

print("\nSTATUS:")
print(state.status)

print(
    "awaiting_user_input:",
    state.awaiting_user_input,
)

print(
    "steps:",
    state.steps,
)


# ============================================================
# TURN 2
# USER PROVIDES ORDER ID
# ============================================================

if state.awaiting_user_input:

    print("\nUSER:")
    print("8452")

    state = agent.resume_with_user_input(
        state,
        "8452",
    )

    print("\nAGENT:")
    print(state.final_message)

    print("\nSTATUS:")
    print(state.status)

    print(
        "order_id:",
        state.order_id,
    )

    print(
        "days_delayed:",
        state.days_delayed,
    )

    print(
        "awaiting_approval:",
        state.awaiting_approval,
    )

    print(
        "steps:",
        state.steps,
    )


# ============================================================
# TURN 3
# HUMAN APPROVES WRITE ACTION
# ============================================================

if state.awaiting_approval:

    print("\nUSER:")
    print("بله، تیکت را ثبت کن.")

    state = agent.resume_with_approval(
        state,
        approved=True,
    )

    print("\nAGENT:")
    print(state.final_message)


# ============================================================
# FINAL STATE
# ============================================================

print("\n" + "=" * 70)
print("FINAL STATE")
print("=" * 70)

print(
    "status:",
    state.status,
)

print(
    "order_id:",
    state.order_id,
)

print(
    "order_status:",
    state.order_status,
)

print(
    "days_delayed:",
    state.days_delayed,
)

print(
    "human_approved:",
    state.human_approved,
)

print(
    "ticket_id:",
    state.ticket_id,
)

print(
    "steps:",
    state.steps,
)

print(
    "finished:",
    state.finished,
)


# ============================================================
# AUDIT TRACE
# ============================================================

agent.audit.print_summary()