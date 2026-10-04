from app.agent import ControlledOrderAgent
from app.planner import RuleBasedPlanner


print("====================================")
print("END-TO-END AGENT TEST")
print("====================================")


# ============================================================
# CREATE AGENT
# ============================================================

planner = RuleBasedPlanner()

agent = ControlledOrderAgent(
    planner=planner,
)


# ============================================================
# USER REQUEST
# ============================================================

user_message = (
    "وضعیت سفارش 8452 را بگو و "
    "اگر بیش از سه روز تأخیر داشت تیکت بساز."
)


print("\nUSER:")
print(user_message)


# ============================================================
# FIRST AGENT EXECUTION
# ============================================================

state = agent.run(
    user_message
)


print("\n--- STATE AFTER FIRST RUN ---")

print("status:", state.status)
print("order_id:", state.order_id)
print("order_status:", state.order_status)
print("days_delayed:", state.days_delayed)
print("steps:", state.steps)
print("awaiting_approval:", state.awaiting_approval)
print("human_approved:", state.human_approved)
print("ticket_id:", state.ticket_id)
print("finished:", state.finished)

print("\nAGENT:")
print(state.final_message)


# ============================================================
# HUMAN APPROVAL
# ============================================================

if state.awaiting_approval:

    print("\nHUMAN:")
    print("Yes, create the ticket.")

    state = agent.resume_with_approval(
        state,
        approved=True,
    )


# ============================================================
# FINAL STATE
# ============================================================

print("\n--- FINAL STATE ---")

print("status:", state.status)
print("order_id:", state.order_id)
print("order_status:", state.order_status)
print("days_delayed:", state.days_delayed)
print("steps:", state.steps)
print("awaiting_approval:", state.awaiting_approval)
print("human_approved:", state.human_approved)
print("ticket_id:", state.ticket_id)
print("finished:", state.finished)

print("\nAGENT:")
print(state.final_message)
agent.audit.print_summary()