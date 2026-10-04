from __future__ import annotations

from app.observability.audit import AuditLogger
from controlled_agent.planners import BasePlanner
from controlled_agent.policy import (
    MAX_STEPS,
    PolicyDecision,
    can_continue_execution,
    evaluate_tool_policy,
)
from controlled_agent.domain.schemas import AgentAction
from controlled_agent.domain.state import (
    AgentState,
    AgentStatus,
    increment_step,
    mark_escalated,
    mark_failed,
    mark_finished,
    mark_waiting_for_input,
    set_status,
    update_user_input,
)
from controlled_agent.tools.ticket import create_ticket
from controlled_agent.tools.order import (
    LookupOrderTimeoutError,
    lookup_order_with_retry,
)


class ControlledOrderAgent:
    """
    Runtime of the controlled order-tracking Agent.

    Responsibilities:
    - Maintain conversation State
    - Ask Planner for next action
    - Enforce Policy independently from Planner
    - Execute READ / WRITE tools
    - Pause for missing user input
    - Pause for Human Approval
    - Enforce MAX_STEPS
    - Record operational Audit events
    - Support controlled security simulations
    """

    def __init__(
        self,
        planner: BasePlanner,
        *,
        simulate_lookup_injection: bool = False,
        simulate_lookup_timeout: bool = False,
    ) -> None:

        self.planner = planner
        self.audit = AuditLogger()

        self.simulate_lookup_injection = (
            simulate_lookup_injection
        )

        self.simulate_lookup_timeout = (
            simulate_lookup_timeout
        )

    # ========================================================
    # START NEW CONVERSATION
    # ========================================================

    def run(
        self,
        user_message: str,
    ) -> AgentState:
        """
        Start a new Agent execution.
        """

        self.audit.clear()

        state = AgentState(
            user_message=user_message,
            latest_user_message=user_message,
        )

        self.audit.log(
            step=0,
            event="request_received",
            detail="New user request received.",
        )

        return self._execute(state)

    # ========================================================
    # RESUME WITH NEW USER INPUT
    # ========================================================

    def resume_with_user_input(
        self,
        state: AgentState,
        user_message: str,
    ) -> AgentState:
        """
        Continue a multi-turn conversation.

        Example:

        Agent:
            Please provide your order ID.

        User:
            8452
        """

        if (
            state.status
            != AgentStatus.WAITING_FOR_INPUT
        ):
            self.audit.log(
                step=state.steps,
                event="user_input_error",
                detail=(
                    "User input received while Agent "
                    "was not waiting for input."
                ),
            )

            return mark_failed(
                state,
                (
                    "Agent is not currently "
                    "waiting for user input."
                ),
            )

        update_user_input(
            state,
            user_message,
        )

        self.audit.log(
            step=state.steps,
            event="user_input_received",
            detail="Additional user input received.",
        )

        return self._execute(state)

    # ========================================================
    # RESUME AFTER HUMAN APPROVAL
    # ========================================================

    def resume_with_approval(
        self,
        state: AgentState,
        approved: bool,
    ) -> AgentState:
        """
        Continue after a sensitive WRITE action
        has been explicitly approved or denied.
        """

        if (
            state.status
            != AgentStatus.WAITING_FOR_APPROVAL
        ):

            self.audit.log(
                step=state.steps,
                event="approval_error",
                detail=(
                    "Approval received while Agent "
                    "was not waiting for approval."
                ),
            )

            return mark_failed(
                state,
                (
                    "Agent is not waiting "
                    "for approval."
                ),
            )

        state.awaiting_approval = False
        state.human_approved = approved
        state.final_message = None

        self.audit.log(
            step=state.steps,
            event="approval_received",
            detail=(
                f"Explicit human approval = {approved}"
            ),
        )

        set_status(
            state,
            AgentStatus.DECIDING,
        )

        return self._execute(state)

    # ========================================================
    # MAIN EXECUTION LOOP
    # ========================================================

    def _execute(
        self,
        state: AgentState,
    ) -> AgentState:

        while not state.finished:

            # ------------------------------------------------
            # MAX STEPS
            # ------------------------------------------------

            if not can_continue_execution(
                state.steps
            ):

                self.audit.log(
                    step=state.steps,
                    event="max_steps_reached",
                    detail=(
                        f"Execution stopped at "
                        f"MAX_STEPS={MAX_STEPS}."
                    ),
                )

                return mark_escalated(
                    state,
                    (
                        f"Maximum Agent steps "
                        f"({MAX_STEPS}) reached. "
                        "Request escalated to a human."
                    ),
                )

            # ------------------------------------------------
            # PLANNER
            # ------------------------------------------------

            set_status(
                state,
                AgentStatus.PLANNING,
            )

            try:

                decision = self.planner.decide(
                    state
                )

            except Exception as exc:

                self.audit.log(
                    step=state.steps,
                    event="planner_failed",
                    detail=str(exc),
                )

                return mark_failed(
                    state,
                    (
                        "Planner failed: "
                        + str(exc)
                    ),
                )

            increment_step(state)

            self.audit.log(
                step=state.steps,
                event="planner_decision",
                detail=(
                    f"action={decision.action.value}"
                ),
            )

            # =================================================
            # ASK ORDER ID
            # =================================================

            if (
                decision.action
                == AgentAction.ASK_ORDER_ID
            ):

                message = (
                    decision.message
                    or (
                        "Please provide "
                        "your order ID."
                    )
                )

                self.audit.log(
                    step=state.steps,
                    event="user_input_requested",
                    detail=(
                        "Agent requires order_id "
                        "before continuing."
                    ),
                )

                return mark_waiting_for_input(
                    state,
                    message,
                )

            # =================================================
            # LOOKUP ORDER
            # =================================================

            if (
                decision.action
                == AgentAction.LOOKUP_ORDER
            ):

                set_status(
                    state,
                    AgentStatus.LOOKING_UP_ORDER,
                )

                # --------------------------------------------
                # POLICY
                # --------------------------------------------

                policy_result = (
                    evaluate_tool_policy(
                        tool_name="lookup_order",
                    )
                )

                self.audit.log(
                    step=state.steps,
                    event="policy_check",
                    detail=(
                        "lookup_order -> "
                        f"{policy_result.value}"
                    ),
                )

                if (
                    policy_result
                    != PolicyDecision.ALLOW
                ):

                    self.audit.log(
                        step=state.steps,
                        event="policy_block",
                        detail=(
                            "lookup_order blocked."
                        ),
                    )

                    return mark_failed(
                        state,
                        (
                            "Policy blocked "
                            "lookup_order."
                        ),
                    )

                # --------------------------------------------
                # ORDER ID
                # --------------------------------------------

                order_id = (
                    decision.order_id
                    or state.order_id
                )

                if order_id is None:

                    self.audit.log(
                        step=state.steps,
                        event="validation_failed",
                        detail="order_id is missing.",
                    )

                    return mark_failed(
                        state,
                        "order_id is missing.",
                    )

                self.audit.log(
                    step=state.steps,
                    event="lookup_order_called",
                    detail=(
                        f"order_id={order_id}"
                    ),
                )

                # --------------------------------------------
                # TOOL EXECUTION
                # --------------------------------------------

                try:

                    result = (
                        lookup_order_with_retry(
                            order_id,
                            simulate_timeout=(
                                self.simulate_lookup_timeout
                            ),
                            simulate_injection=(
                                self.simulate_lookup_injection
                            ),
                        )
                    )

                except LookupOrderTimeoutError:

                    self.audit.log(
                        step=state.steps,
                        event="tool_timeout",
                        detail=(
                            "lookup_order failed "
                            "after retry limit."
                        ),
                    )

                    return mark_failed(
                        state,
                        (
                            "lookup_order failed "
                            "after retry limit."
                        ),
                    )

                except Exception as exc:

                    self.audit.log(
                        step=state.steps,
                        event="tool_failed",
                        detail=(
                            "lookup_order: "
                            + str(exc)
                        ),
                    )

                    return mark_failed(
                        state,
                        (
                            "lookup_order failed: "
                            + str(exc)
                        ),
                    )

                # --------------------------------------------
                # SAFE VALIDATED RESULT
                # --------------------------------------------

                state.order_id = (
                    result.order_id
                )

                state.order_status = (
                    result.status
                )

                state.days_delayed = (
                    result.days_delayed
                )

                self.audit.log(
                    step=state.steps,
                    event="tool_output_validated",
                    detail=(
                        f"lookup_order validated; "
                        f"status={result.status.value}, "
                        f"days_delayed="
                        f"{result.days_delayed}"
                    ),
                )

                set_status(
                    state,
                    AgentStatus.DECIDING,
                )

                continue

            # =================================================
            # REQUEST HUMAN APPROVAL
            # =================================================

            if (
                decision.action
                == AgentAction.REQUEST_APPROVAL
            ):

                policy_result = (
                    evaluate_tool_policy(
                        tool_name="create_ticket",
                        days_delayed=(
                            state.days_delayed
                        ),
                        human_approved=(
                            state.human_approved
                        ),
                    )
                )

                self.audit.log(
                    step=state.steps,
                    event="policy_check",
                    detail=(
                        "create_ticket -> "
                        f"{policy_result.value}"
                    ),
                )

                # --------------------------------------------
                # DENIED
                # --------------------------------------------

                if (
                    policy_result
                    == PolicyDecision.DENY
                ):

                    self.audit.log(
                        step=state.steps,
                        event="policy_block",
                        detail=(
                            "Ticket creation denied."
                        ),
                    )

                    return mark_failed(
                        state,
                        (
                            "Policy does not allow "
                            "ticket creation for "
                            "this order."
                        ),
                    )

                # --------------------------------------------
                # REQUIRE HUMAN APPROVAL
                # --------------------------------------------

                if (
                    policy_result
                    == PolicyDecision.REQUIRE_APPROVAL
                ):

                    state.awaiting_approval = True

                    set_status(
                        state,
                        AgentStatus.WAITING_FOR_APPROVAL,
                    )

                    state.final_message = (
                        decision.message
                        or (
                            "Human approval "
                            "is required."
                        )
                    )

                    self.audit.log(
                        step=state.steps,
                        event="approval_requested",
                        detail=(
                            "WRITE action paused "
                            "until explicit "
                            "human approval."
                        ),
                    )

                    return state

                continue

            # =================================================
            # CREATE TICKET
            # =================================================

            if (
                decision.action
                == AgentAction.CREATE_TICKET
            ):

                # --------------------------------------------
                # INDEPENDENT POLICY GATE
                # --------------------------------------------

                policy_result = (
                    evaluate_tool_policy(
                        tool_name="create_ticket",
                        days_delayed=(
                            state.days_delayed
                        ),
                        human_approved=(
                            state.human_approved
                        ),
                    )
                )

                self.audit.log(
                    step=state.steps,
                    event="policy_check",
                    detail=(
                        "create_ticket -> "
                        f"{policy_result.value}"
                    ),
                )

                if (
                    policy_result
                    != PolicyDecision.ALLOW
                ):

                    self.audit.log(
                        step=state.steps,
                        event="write_blocked",
                        detail=(
                            "create_ticket blocked "
                            "by Policy Layer."
                        ),
                    )

                    return mark_failed(
                        state,
                        (
                            "Policy blocked "
                            "create_ticket."
                        ),
                    )

                # --------------------------------------------
                # REQUIRED STATE
                # --------------------------------------------

                if state.order_id is None:

                    self.audit.log(
                        step=state.steps,
                        event="validation_failed",
                        detail="order_id is missing.",
                    )

                    return mark_failed(
                        state,
                        "order_id is missing.",
                    )

                if state.days_delayed is None:

                    self.audit.log(
                        step=state.steps,
                        event="validation_failed",
                        detail=(
                            "days_delayed "
                            "is missing."
                        ),
                    )

                    return mark_failed(
                        state,
                        (
                            "days_delayed "
                            "is missing."
                        ),
                    )

                # --------------------------------------------
                # WRITE TOOL
                # --------------------------------------------

                set_status(
                    state,
                    AgentStatus.CREATING_TICKET,
                )

                idempotency_key = (
                    f"ticket:"
                    f"{state.order_id}:delay"
                )

                reason = (
                    f"Order delayed "
                    f"{state.days_delayed} days"
                )

                self.audit.log(
                    step=state.steps,
                    event="create_ticket_called",
                    detail=(
                        f"order_id={state.order_id}"
                    ),
                )

                try:

                    ticket = create_ticket(
                        order_id=state.order_id,
                        reason=reason,
                        idempotency_key=(
                            idempotency_key
                        ),
                    )

                except Exception as exc:

                    self.audit.log(
                        step=state.steps,
                        event="write_tool_failed",
                        detail=str(exc),
                    )

                    return mark_failed(
                        state,
                        (
                            "create_ticket failed: "
                            + str(exc)
                        ),
                    )

                state.ticket_id = (
                    ticket.ticket_id
                )

                self.audit.log(
                    step=state.steps,
                    event="ticket_created",
                    detail=(
                        f"ticket_id="
                        f"{ticket.ticket_id}, "
                        f"status={ticket.status}"
                    ),
                )

                # --------------------------------------------
                # DIRECT SAFE FINAL RESPONSE
                # --------------------------------------------

                final_message = (
                    f"تیکت پشتیبانی با شناسه "
                    f"{ticket.ticket_id} "
                    "با موفقیت ثبت شده است."
                )

                self.audit.log(
                    step=state.steps,
                    event="final_response",
                    detail=final_message,
                )

                return mark_finished(
                    state,
                    final_message,
                )

            # =================================================
            # RESPOND
            # =================================================

            if (
                decision.action
                == AgentAction.RESPOND
            ):

                message = (
                    decision.message
                    or "Request completed."
                )

                self.audit.log(
                    step=state.steps,
                    event="final_response",
                    detail=message,
                )

                return mark_finished(
                    state,
                    message,
                )

            # =================================================
            # ESCALATE
            # =================================================

            if (
                decision.action
                == AgentAction.ESCALATE
            ):

                message = (
                    decision.message
                    or (
                        "Request escalated "
                        "to a human operator."
                    )
                )

                self.audit.log(
                    step=state.steps,
                    event="escalated",
                    detail=message,
                )

                return mark_escalated(
                    state,
                    message,
                )

            # =================================================
            # STOP
            # =================================================

            if (
                decision.action
                == AgentAction.STOP
            ):

                message = (
                    decision.message
                    or "Agent stopped."
                )

                self.audit.log(
                    step=state.steps,
                    event="agent_stopped",
                    detail=message,
                )

                return mark_finished(
                    state,
                    message,
                )

            # =================================================
            # UNKNOWN ACTION
            # =================================================

            self.audit.log(
                step=state.steps,
                event="unsupported_action",
                detail=str(
                    decision.action
                ),
            )

            return mark_failed(
                state,
                (
                    "Planner returned "
                    "an unsupported action."
                ),
            )

        return state