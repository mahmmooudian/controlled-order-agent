from __future__ import annotations

from fastapi import APIRouter

from controlled_agent import __version__
from controlled_agent.api.schemas import (
    HealthResponse,
    ReadinessResponse,
)


router = APIRouter(
    tags=["health"],
)


@router.get(
    "/health",
    response_model=HealthResponse,
)
def health_check() -> HealthResponse:
    """
    Lightweight liveness endpoint.
    """

    return HealthResponse(
        status="ok",
        service="controlled-order-agent",
        version=__version__,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
)
def readiness_check() -> ReadinessResponse:
    """
    Basic readiness endpoint.

    More infrastructure-specific checks can
    be added later without changing /health.
    """

    return ReadinessResponse(
        ready=True,
        service="controlled-order-agent",
    )