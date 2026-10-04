from __future__ import annotations

import re

from controlled_agent.policy import can_offer_ticket

from controlled_agent.domain.schemas import (
    AgentAction,
    AgentDecision,
    OrderStatus,
)
from controlled_agent.domain.state import AgentState
from controlled_agent.planners.base import BasePlanner


class RuleBasedPlanner(BasePlanner):
    """
    Deterministic planner used for:

    - local testing
    - offline demo
    - fallback when LLM API is unavailable

    The real LLM planner implements the same interface.
    """

    ORDER_ID_PATTERN = re.compile(
        r"\b(\d{4,12})\b"
    )

    def decide(
        self,
        state: AgentState,
    ) -> AgentDecision:

        # ----------------------------------------------------
        # CASE 1: Agent already finished
        # ----------------------------------------------------

        if state.finished:
            return AgentDecision(
                action=AgentAction.STOP,
            )

        # ----------------------------------------------------
        # CASE 2: We do not have an order_id yet
        # ----------------------------------------------------

        if state.order_id is None:

            match = self.ORDER_ID_PATTERN.search(
                state.user_message
            )

            if match is None:
                return AgentDecision(
                    action=AgentAction.ASK_ORDER_ID,
                    message=(
                        "لطفاً شماره سفارش خود را "
                        "ارسال کنید."
                    ),
                )

            return AgentDecision(
                action=AgentAction.LOOKUP_ORDER,
                order_id=match.group(1),
            )

        # ----------------------------------------------------
        # CASE 3: We have order_id but no order data yet
        # ----------------------------------------------------

        if state.order_status is None:
            return AgentDecision(
                action=AgentAction.LOOKUP_ORDER,
                order_id=state.order_id,
            )

        # ----------------------------------------------------
        # CASE 4: Order does not exist
        # ----------------------------------------------------

        if (
            state.order_status
            == OrderStatus.NOT_FOUND
        ):
            return AgentDecision(
                action=AgentAction.RESPOND,
                message=(
                    "سفارشی با این شماره پیدا نشد."
                ),
            )

        # ----------------------------------------------------
        # CASE 5: Delay > 3 days
        # ----------------------------------------------------

        if can_offer_ticket(
            state.days_delayed
        ):

            # Ticket already exists / created
            if state.ticket_id is not None:
                return AgentDecision(
                    action=AgentAction.RESPOND,
                    message=(
                        f"تیکت پشتیبانی با شناسه "
                        f"{state.ticket_id} با موفقیت "
                        "ثبت شده است."
                    ),
                )

            # No human approval decision yet
            if state.human_approved is None:
                return AgentDecision(
                    action=(
                        AgentAction.REQUEST_APPROVAL
                    ),
                    message=(
                        f"سفارش {state.order_id} "
                        f"{state.days_delayed} روز "
                        "تأخیر دارد. آیا اجازه می‌دهید "
                        "یک تیکت پشتیبانی ثبت کنم؟"
                    ),
                )

            # Explicit human approval received
            if state.human_approved is True:
                return AgentDecision(
                    action=AgentAction.CREATE_TICKET,
                    order_id=state.order_id,
                )

            # Explicit human denial
            return AgentDecision(
                action=AgentAction.RESPOND,
                message=(
                    "ایجاد تیکت توسط کاربر "
                    "تأیید نشد."
                ),
            )

        # ----------------------------------------------------
        # CASE 6: No ticket is required
        # ----------------------------------------------------

        return AgentDecision(
            action=AgentAction.RESPOND,
            message=(
                f"وضعیت سفارش {state.order_id}: "
                f"{state.order_status.value}. "
                f"میزان تأخیر: "
                f"{state.days_delayed} روز."
            ),
        )