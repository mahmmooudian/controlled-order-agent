from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# ENUMS
# ============================================================

class OrderStatus(str, Enum):
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELAYED = "delayed"
    DELIVERED = "delivered"
    NOT_FOUND = "not_found"


class ToolPermission(str, Enum):
    READ = "read"
    WRITE = "write"


class AgentAction(str, Enum):
    ASK_ORDER_ID = "ask_order_id"
    LOOKUP_ORDER = "lookup_order"
    REQUEST_APPROVAL = "request_approval"
    CREATE_TICKET = "create_ticket"
    RESPOND = "respond"
    STOP = "stop"
    ESCALATE = "escalate"


# ============================================================
# LOOKUP ORDER - READ TOOL
# ============================================================

class LookupOrderInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    order_id: str = Field(
        ...,
        min_length=4,
        max_length=12,
        pattern=r"^\d+$",
        description="Numeric order identifier",
    )


class LookupOrderOutput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    order_id: str = Field(
        ...,
        min_length=4,
        max_length=12,
        pattern=r"^\d+$",
    )

    status: OrderStatus

    days_delayed: int = Field(
        ...,
        ge=0,
        le=365,
    )


# ============================================================
# CREATE TICKET - WRITE TOOL
# ============================================================

class CreateTicketInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    order_id: str = Field(
        ...,
        min_length=4,
        max_length=12,
        pattern=r"^\d+$",
    )

    reason: str = Field(
        ...,
        min_length=5,
        max_length=300,
    )

    idempotency_key: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )


class CreateTicketOutput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    ticket_id: str = Field(
        ...,
        min_length=3,
        max_length=64,
    )

    status: Literal[
        "created",
        "existing",
    ]


# ============================================================
# LLM PLANNER OUTPUT
# ============================================================

class AgentDecision(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    action: AgentAction

    order_id: Optional[str] = None

    message: Optional[str] = Field(
        default=None,
        max_length=500,
    )


# ============================================================
# HUMAN APPROVAL
# ============================================================

class HumanApproval(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    approved: bool

    action: Literal["create_ticket"]

    order_id: str = Field(
        ...,
        min_length=4,
        max_length=12,
        pattern=r"^\d+$",
    )