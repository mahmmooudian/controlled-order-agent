from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from controlled_agent import (
    __version__,
)
from controlled_agent.api.dependencies import (
    get_database_readiness,
)
from controlled_agent.api.schemas import (
    HealthResponse,
    ReadinessResponse,
)


router = APIRouter(
    tags=["health"],
)


# ============================================================
# LIVENESS
# ============================================================

@router.get(
    "/health",
    response_model=HealthResponse,
)
def health_check() -> HealthResponse:
    """
    Lightweight liveness endpoint.

    This endpoint only verifies that the
    application process is running.
    """

    return HealthResponse(
        status="ok",
        service="controlled-order-agent",
        version=__version__,
    )


# ============================================================
# READINESS
# ============================================================

@router.get(
    "/ready",
    response_model=ReadinessResponse,
)
def readiness_check(
    database_ready: bool = Depends(
        get_database_readiness
    ),
) -> ReadinessResponse:
    """
    Verify that the application is ready
    to serve Agent requests.

    Readiness currently requires a healthy
    SQLite persistence layer.
    """

    if not database_ready:
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Database is not ready."
            ),
        )

    return ReadinessResponse(
        ready=True,
        service="controlled-order-agent",
    )