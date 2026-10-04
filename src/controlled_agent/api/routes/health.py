from __future__ import annotations

from fastapi import APIRouter

from controlled_agent import __version__
from controlled_agent.api.schemas import HealthResponse


router = APIRouter(
    tags=["health"],
)


@router.get(
    "/health",
    response_model=HealthResponse,
)
def health_check() -> HealthResponse:
    """
    Lightweight service health endpoint.
    """

    return HealthResponse(
        status="ok",
        service="controlled-order-agent",
        version=__version__,
    )