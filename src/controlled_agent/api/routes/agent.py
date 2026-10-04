from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from controlled_agent.api.dependencies import (
    get_agent,
)
from controlled_agent.api.schemas import (
    AgentRunResponse,
    CreateAgentRunRequest,
)
from controlled_agent.domain.state import AgentState
from controlled_agent.runtime import ControlledOrderAgent


router = APIRouter(
    prefix="/agent",
    tags=["agent"],
)


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
    Create and execute a new controlled Agent run.
    """

    state = agent.run(
        request.message
    )

    run_id = agent.current_run_id

    if run_id is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "Agent run was created without "
                "a persistent run_id."
            ),
        )

    return _state_to_response(
        run_id=run_id,
        state=state,
    )