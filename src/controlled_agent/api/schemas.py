from __future__ import annotations

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


# ============================================================
# HEALTH
# ============================================================

class HealthResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    status: str
    service: str
    version: str


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    ready: bool
    service: str


# ============================================================
# CREATE RUN
# ============================================================

class CreateAgentRunRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    message: str = Field(
        min_length=1,
        max_length=4000,
    )


# ============================================================
# CONTINUE RUN WITH USER INPUT
# ============================================================

class AgentInputRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    message: str = Field(
        min_length=1,
        max_length=4000,
    )


# ============================================================
# HUMAN APPROVAL
# ============================================================

class AgentApprovalRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    approved: bool


# ============================================================
# PUBLIC RUN RESPONSE
# ============================================================

class AgentRunResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    run_id: str
    status: str
    steps: int
    finished: bool
    awaiting_user_input: bool
    awaiting_approval: bool

    order_id: str | None = None
    order_status: str | None = None
    days_delayed: int | None = None
    ticket_id: str | None = None
    final_message: str | None = None


# ============================================================
# AUDIT / EXECUTION TRACE
# ============================================================

class AuditEventResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    timestamp: str
    step: int
    event: str
    detail: str