from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from controlled_agent.api.dependencies import (
    get_agent,
    get_audit_repository,
)
from controlled_agent.api.schemas import (
    AgentApprovalRequest,
    AgentInputRequest,
    AgentRunResponse,
    AuditEventResponse,
    CreateAgentRunRequest,
)
from controlled_agent.domain.state import (
    AgentState,
    AgentStatus,
)
from controlled_agent.persistence import (
    AuditRepository,
)
from controlled_agent.runtime import (
    ControlledOrderAgent,
)


router = APIRouter(
    prefix="/agent",
    tags=["agent"],
)


# ============================================================
# RESPONSE MAPPING
# ============================================================

def _state_to_response(
    *,
    run_id: str,
    state: AgentState,
) -> AgentRunResponse:
    """
    Convert internal AgentState into
    a stable public API response.
    """

    order_status = None

    if state.order_status is not None:
        order_status = (
            state.order_status.value
        )

    return AgentRunResponse(
        run_id=run_id,
        status=state.status.value,
        steps=state.steps,
        finished=state.finished,
        awaiting_user_input=(
            state.awaiting_user_input
        ),
        awaiting_approval=(
            state.awaiting_approval
        ),
        order_id=state.order_id,
        order_status=order_status,
        days_delayed=state.days_delayed,
        ticket_id=state.ticket_id,
        final_message=state.final_message,
    )


# ============================================================
# LOAD RUN
# ============================================================

def _load_run_or_404(
    *,
    agent: ControlledOrderAgent,
    run_id: str,
) -> AgentState:
    """
    Restore a persisted Agent run.

    HTTP 404 is returned when the requested
    run does not exist.
    """

    state = agent.load_run(
        run_id
    )

    if state is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Agent run not found.",
        )

    return state


# ============================================================
# CREATE RUN
# ============================================================

@router.post(
    "/runs",
    response_model=AgentRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_agent_run(
    request: CreateAgentRunRequest,
    agent: ControlledOrderAgent = Depends(
        get_agent
    ),
) -> AgentRunResponse:
    """
    Create and execute a new controlled
    Agent run.
    """

    state = agent.run(
        request.message
    )

    run_id = agent.current_run_id

    if run_id is None:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Agent run was created without "
                "a persistent run_id."
            ),
        )

    return _state_to_response(
        run_id=run_id,
        state=state,
    )


# ============================================================
# GET RUN
# ============================================================

@router.get(
    "/runs/{run_id}",
    response_model=AgentRunResponse,
)
def get_agent_run(
    run_id: str,
    agent: ControlledOrderAgent = Depends(
        get_agent
    ),
) -> AgentRunResponse:
    """
    Return the current persisted state
    of one Agent run.
    """

    state = _load_run_or_404(
        agent=agent,
        run_id=run_id,
    )

    return _state_to_response(
        run_id=run_id,
        state=state,
    )


# ============================================================
# CONTINUE WITH USER INPUT
# ============================================================

@router.post(
    "/runs/{run_id}/input",
    response_model=AgentRunResponse,
)
def continue_agent_run(
    run_id: str,
    request: AgentInputRequest,
    agent: ControlledOrderAgent = Depends(
        get_agent
    ),
) -> AgentRunResponse:
    """
    Continue an Agent run that is waiting
    for additional user input.
    """

    state = _load_run_or_404(
        agent=agent,
        run_id=run_id,
    )

    if (
        state.status
        != AgentStatus.WAITING_FOR_INPUT
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Agent run is not waiting "
                "for user input. "
                f"Current status: "
                f"{state.status.value}"
            ),
        )

    result = (
        agent.resume_with_user_input(
            state,
            request.message,
        )
    )

    return _state_to_response(
        run_id=run_id,
        state=result,
    )


# ============================================================
# HUMAN APPROVAL
# ============================================================

@router.post(
    "/runs/{run_id}/approval",
    response_model=AgentRunResponse,
)
def decide_agent_approval(
    run_id: str,
    request: AgentApprovalRequest,
    agent: ControlledOrderAgent = Depends(
        get_agent
    ),
) -> AgentRunResponse:
    """
    Approve or deny a sensitive WRITE action.

    The Runtime performs the final persistent
    approval validation before execution.
    """

    state = _load_run_or_404(
        agent=agent,
        run_id=run_id,
    )

    if (
        state.status
        != AgentStatus.WAITING_FOR_APPROVAL
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Agent run is not waiting "
                "for human approval. "
                f"Current status: "
                f"{state.status.value}"
            ),
        )

    result = (
        agent.resume_with_approval(
            state,
            approved=request.approved,
        )
    )

    return _state_to_response(
        run_id=run_id,
        state=result,
    )


# ============================================================
# AUDIT / EXECUTION TRACE
# ============================================================

@router.get(
    "/runs/{run_id}/audit",
    response_model=list[AuditEventResponse],
)
def get_agent_run_audit(
    run_id: str,
    agent: ControlledOrderAgent = Depends(
        get_agent
    ),
    audit_repository: AuditRepository = Depends(
        get_audit_repository
    ),
) -> list[AuditEventResponse]:
    """
    Return the persisted execution trace
    for one Agent run.
    """

    _load_run_or_404(
        agent=agent,
        run_id=run_id,
    )

    events = (
        audit_repository.get_for_run(
            run_id
        )
    )

    return [
        AuditEventResponse(
            timestamp=event.timestamp,
            step=event.step,
            event=event.event,
            detail=event.detail,
        )
        for event in events
    ]