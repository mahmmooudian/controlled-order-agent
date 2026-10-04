from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from controlled_agent.domain.schemas import OrderStatus


# ============================================================
# AGENT EXECUTION STATUS
# ============================================================

class AgentStatus(str, Enum):
    RECEIVED = "received"

    # Agent is waiting for more information from the user,
    # for example when order_id is missing.
    WAITING_FOR_INPUT = "waiting_for_input"

    VALIDATING_INPUT = "validating_input"
    PLANNING = "planning"
    LOOKING_UP_ORDER = "looking_up_order"
    VALIDATING_TOOL_OUTPUT = "validating_tool_output"
    DECIDING = "deciding"

    # Agent is paused before a sensitive WRITE action.
    WAITING_FOR_APPROVAL = "waiting_for_approval"

    CREATING_TICKET = "creating_ticket"

    DONE = "done"
    FAILED = "failed"
    ESCALATED = "escalated"


# ============================================================
# AGENT STATE
# ============================================================

class AgentState(BaseModel):
    """
    Central state object for the controlled order-tracking Agent.

    It stores only operational information required
    for execution and decision-making.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    # --------------------------------------------------------
    # CONVERSATION
    # --------------------------------------------------------

    user_message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
    )

    # Stores the latest user input in a multi-turn flow.
    latest_user_message: Optional[str] = None

    # --------------------------------------------------------
    # ORDER INFORMATION
    # --------------------------------------------------------

    order_id: Optional[str] = None

    order_status: Optional[OrderStatus] = None

    days_delayed: Optional[int] = Field(
        default=None,
        ge=0,
        le=365,
    )

    # --------------------------------------------------------
    # HUMAN APPROVAL
    # --------------------------------------------------------

    awaiting_approval: bool = False

    human_approved: Optional[bool] = None

    # --------------------------------------------------------
    # TICKET INFORMATION
    # --------------------------------------------------------

    ticket_id: Optional[str] = None

    # --------------------------------------------------------
    # EXECUTION CONTROL
    # --------------------------------------------------------

    steps: int = Field(
        default=0,
        ge=0,
    )

    status: AgentStatus = AgentStatus.RECEIVED

    finished: bool = False

    # --------------------------------------------------------
    # USER INTERACTION CONTROL
    # --------------------------------------------------------

    awaiting_user_input: bool = False

    # --------------------------------------------------------
    # FINAL / CURRENT AGENT MESSAGE
    # --------------------------------------------------------

    final_message: Optional[str] = None


# ============================================================
# STATE HELPERS
# ============================================================

def increment_step(
    state: AgentState,
) -> AgentState:
    """
    Increase the Agent execution step counter.
    """

    state.steps += 1

    return state


def set_status(
    state: AgentState,
    status: AgentStatus,
) -> AgentState:
    """
    Update Agent execution status.
    """

    state.status = status

    return state


# ============================================================
# WAITING FOR USER INPUT
# ============================================================

def mark_waiting_for_input(
    state: AgentState,
    message: str,
) -> AgentState:
    """
    Pause execution until the user provides
    additional information.

    This is different from DONE because
    the conversation can continue later.
    """

    state.finished = False
    state.awaiting_user_input = True
    state.status = AgentStatus.WAITING_FOR_INPUT
    state.final_message = message

    return state


# ============================================================
# WAITING FOR HUMAN APPROVAL
# ============================================================

def mark_waiting_for_approval(
    state: AgentState,
    message: str,
) -> AgentState:
    """
    Pause execution before a sensitive WRITE action.
    """

    state.finished = False
    state.awaiting_approval = True
    state.status = AgentStatus.WAITING_FOR_APPROVAL
    state.final_message = message

    return state


# ============================================================
# FINISHED
# ============================================================

def mark_finished(
    state: AgentState,
    message: str,
) -> AgentState:
    """
    Mark execution as successfully completed.
    """

    state.finished = True

    state.awaiting_user_input = False
    state.awaiting_approval = False

    state.status = AgentStatus.DONE
    state.final_message = message

    return state


# ============================================================
# FAILED
# ============================================================

def mark_failed(
    state: AgentState,
    message: str,
) -> AgentState:
    """
    Mark execution as failed safely.
    """

    state.finished = True

    state.awaiting_user_input = False
    state.awaiting_approval = False

    state.status = AgentStatus.FAILED
    state.final_message = message

    return state


# ============================================================
# ESCALATED
# ============================================================

def mark_escalated(
    state: AgentState,
    message: str,
) -> AgentState:
    """
    Escalate the request to a human operator.
    """

    state.finished = True

    state.awaiting_user_input = False
    state.awaiting_approval = False

    state.status = AgentStatus.ESCALATED
    state.final_message = message

    return state


# ============================================================
# UPDATE USER INPUT
# ============================================================

def update_user_input(
    state: AgentState,
    user_message: str,
) -> AgentState:
    """
    Update the Agent with a new user message
    during a multi-turn conversation.
    """

    state.latest_user_message = user_message

    state.user_message = user_message

    state.awaiting_user_input = False

    state.final_message = None

    state.status = AgentStatus.RECEIVED

    return state
