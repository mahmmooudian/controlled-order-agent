from __future__ import annotations

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
from controlled_agent.observability.audit import AuditLogger
from controlled_agent.persistence import (
    AgentRunRepository,
    ApprovalRepository,
)
from controlled_agent.planners.base import BasePlanner
from controlled_agent.policy.engine import (
    MAX_STEPS,
    PolicyDecision,
    can_continue_execution,
    evaluate_tool_policy,
)
from controlled_agent.services.ticket import TicketService
from controlled_agent.tools.order import (
    LookupOrderTimeoutError,
    lookup_order_with_retry,
)
from controlled_agent.tools.ticket import create_ticket


class ControlledOrderAgent:
    """
    Runtime of the controlled order-tracking Agent.

    Responsibilities:
    - Maintain conversation state
    - Ask Planner for the next action
    - Enforce Policy independently from Planner
    - Execute READ / WRITE tools
    - Pause for missing user input
    - Pause for Human Approval
    - Enforce MAX_STEPS
    - Record operational Audit events
    - Support controlled security simulations
    - Support dependency injection
    - Persist Agent runs when configured
    - Restore persisted Agent runs
    - Bind Audit events to persistent run IDs
    - Persist Human Approval requests and decisions
    """

    def __init__(
        self,
        planner: BasePlanner,
        *,
        audit_logger: AuditLogger | None = None,
        ticket_service: TicketService | None = None,
        run_repository: AgentRunRepository | None = None,
        approval_repository: ApprovalRepository | None = None,
        simulate_lookup_injection: bool = False,
        simulate_lookup_timeout: bool = False,
    ) -> None:
        """
        Initialize the controlled Agent runtime.

        Optional dependencies can be injected for
        production, persistence, integration testing,
        or alternative implementations.

        Backward compatibility is preserved:

        - If audit_logger is not provided,
          the default in-memory AuditLogger is used.

        - If ticket_service is not provided,
          create_ticket falls back to MockTicketService.

        - If run_repository is not provided,
          Agent state persistence is disabled.

        - If approval_repository is not provided,
          Human Approval works as before without
          persistent approval records.

        Approval persistence requires run persistence
        because approvals are linked to agent_runs
        through a database foreign key.
        """

        if (
            approval_repository is not None
            and run_repository is None
        ):
            raise ValueError(
                "approval_repository requires "
                "run_repository."
            )

        self.planner = planner

        self.audit = (
            audit_logger
            if audit_logger is not None
            else AuditLogger()
        )

        self.ticket_service = ticket_service
        self.run_repository = run_repository
        self.approval_repository = approval_repository

        self.current_run_id: str | None = None

        self.simulate_lookup_injection = (
            simulate_lookup_injection
        )

        self.simulate_lookup_timeout = (
            simulate_lookup_timeout
        )

    # ========================================================
    # PERSISTENCE
    # ========================================================

    def _persist_state(
        self,
        state: AgentState,
    ) -> None:
        """
        Persist the current Agent state when
        AgentRunRepository is configured.

        When a run id becomes available, the
        AuditLogger is automatically bound
        to the same Agent run.
        """

        if self.run_repository is None:
            return

        self.current_run_id = (
            self.run_repository.save(
                state,
                run_id=self.current_run_id,
            )
        )

        self.audit.set_run_id(
            self.current_run_id
        )

    def load_run(
        self,
        run_id: str,
    ) -> AgentState | None:
        """
        Restore a previously persisted Agent run.

        The restored run becomes the active run
        for state persistence, audit logging,
        and approval persistence.
        """

        if self.run_repository is None:
            raise RuntimeError(
                "AgentRunRepository is not configured."
            )

        state = self.run_repository.get(
            run_id
        )

        if state is not None:
            self.current_run_id = run_id

            self.audit.set_run_id(
                run_id
            )

        return state

    # ========================================================
    # APPROVAL PERSISTENCE
    # ========================================================

    def _ensure_pending_approval(
        self,
        *,
        action: str,
    ) -> bool:
        """
        Ensure that exactly one pending approval exists
        for the active Agent run and action.

        Returns True when approval persistence is either
        disabled or successfully available.

        Returns False when persistence is configured but
        the approval request cannot safely be created.
        """

        if self.approval_repository is None:
            return True

        if self.current_run_id is None:
            self.audit.log(
                step=0,
                event="approval_persistence_failed",
                detail=(
                    "Approval persistence is enabled "
                    "but no active run_id exists."
                ),
            )

            return False

        try:
            existing = (
                self.approval_repository
                .get_latest_pending(
                    self.current_run_id,
                    action=action,
                )
            )

            if existing is not None:
                self.audit.log(
                    step=0,
                    event="approval_record_reused",
                    detail=(
                        "Existing pending approval "
                        f"{existing['approval_id']} reused "
                        f"for action={action}."
                    ),
                )

                return True

            created = (
                self.approval_repository
                .create_request(
                    run_id=self.current_run_id,
                    action=action,
                )
            )

            self.audit.log(
                step=0,
                event="approval_record_created",
                detail=(
                    "Persistent approval request "
                    f"{created['approval_id']} created "
                    f"for action={action}."
                ),
            )

            return True

        except Exception as exc:
            self.audit.log(
                step=0,
                event="approval_persistence_failed",
                detail=str(exc),
            )

            return False

    def _persist_approval_decision(
        self,
        *,
        action: str,
        approved: bool,
        step: int,
    ) -> bool:
        """
        Persist an explicit Human Approval decision.

        Security behavior is fail-closed:
        if persistent approval is configured and
        no valid pending approval exists, the WRITE
        operation is not allowed to continue.
        """

        if self.approval_repository is None:
            return True

        if self.current_run_id is None:
            self.audit.log(
                step=step,
                event="approval_decision_failed",
                detail=(
                    "Approval decision cannot be "
                    "persisted without an active run_id."
                ),
            )

            return False

        try:
            pending = (
                self.approval_repository
                .get_latest_pending(
                    self.current_run_id,
                    action=action,
                )
            )

            if pending is None:
                self.audit.log(
                    step=step,
                    event="approval_decision_failed",
                    detail=(
                        "No pending persistent approval "
                        f"exists for action={action}."
                    ),
                )

                return False

            decided = (
                self.approval_repository.decide(
                    pending["approval_id"],
                    approved=approved,
                )
            )

            self.audit.log(
                step=step,
                event="approval_record_decided",
                detail=(
                    f"approval_id="
                    f"{decided['approval_id']}, "
                    f"approved={approved}"
                ),
            )

            return True

        except Exception as exc:
            self.audit.log(
                step=step,
                event="approval_decision_failed",
                detail=str(exc),
            )

            return False

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

        # Detach from any previous persistent run.
        self.current_run_id = None

        self.audit.set_run_id(
            None
        )

        self.audit.clear()

        state = AgentState(
            user_message=user_message,
            latest_user_message=user_message,
        )

        # Create the persistent Agent run first.
        # This also binds the AuditLogger to the
        # generated run_id.
        self._persist_state(
            state
        )

        self.audit.log(
            step=0,
            event="request_received",
            detail="New user request received.",
        )

        result = self._execute(
            state
        )

        self._persist_state(
            result
        )

        return result

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

            result = mark_failed(
                state,
                (
                    "Agent is not currently "
                    "waiting for user input."
                ),
            )

            self._persist_state(
                result
            )

            return result

        update_user_input(
            state,
            user_message,
        )

        self.audit.log(
            step=state.steps,
            event="user_input_received",
            detail="Additional user input received.",
        )

        result = self._execute(
            state
        )

        self._persist_state(
            result
        )

        return result

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

        When ApprovalRepository is configured,
        the decision must be successfully persisted
        before execution is allowed to continue.
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

            result = mark_failed(
                state,
                (
                    "Agent is not waiting "
                    "for approval."
                ),
            )

            self._persist_state(
                result
            )

            return result

        decision_persisted = (
            self._persist_approval_decision(
                action="create_ticket",
                approved=approved,
                step=state.steps,
            )
        )

        if not decision_persisted:
            result = mark_failed(
                state,
                (
                    "Human approval could not be "
                    "validated or persisted safely."
                ),
            )

            self._persist_state(
                result
            )

            return result

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

        result = self._execute(
            state
        )

        self._persist_state(
            result
        )

        return result

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

            increment_step(
                state
            )

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

                    approval_ready = (
                        self._ensure_pending_approval(
                            action="create_ticket",
                        )
                    )

                    if not approval_ready:
                        return mark_failed(
                            state,
                            (
                                "Human approval request "
                                "could not be persisted "
                                "safely."
                            ),
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
                        service=self.ticket_service,
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

                final_message = (
                    "تیکت پشتیبانی با شناسه "
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