from __future__ import annotations

import logging
from time import perf_counter
from uuid import uuid4

from fastapi import (
    FastAPI,
    Request,
)

from controlled_agent import (
    __version__,
)
from controlled_agent.api.config import (
    ApiSettings,
    get_settings,
)
from controlled_agent.api.errors import (
    unhandled_exception_handler,
)
from controlled_agent.api.routes import (
    agent_router,
    health_router,
)


logger = logging.getLogger(
    "controlled_agent.api"
)


# ============================================================
# LOGGING
# ============================================================

def configure_application_logging(
    settings: ApiSettings,
) -> None:
    """
    Configure the application's own logging namespace.

    Uvicorn remains responsible for its own handlers
    and output formatting.
    """

    application_logger = logging.getLogger(
        "controlled_agent"
    )

    application_logger.setLevel(
        getattr(
            logging,
            settings.log_level,
            logging.INFO,
        )
    )


# ============================================================
# APPLICATION FACTORY
# ============================================================

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """

    settings = get_settings()

    configure_application_logging(
        settings
    )

    application = FastAPI(
        title=settings.app_name,
        description=(
            "Policy-controlled AI Agent backend "
            "for safe order tracking and "
            "human-approved actions."
        ),
        version=__version__,
        debug=settings.debug,
    )

    # --------------------------------------------------------
    # GLOBAL SAFE 500 HANDLER
    # --------------------------------------------------------

    application.add_exception_handler(
        Exception,
        unhandled_exception_handler,
    )

    # --------------------------------------------------------
    # REQUEST CORRELATION
    # --------------------------------------------------------

    @application.middleware(
        "http"
    )
    async def request_context_middleware(
        request: Request,
        call_next,
    ):
        """
        Attach a unique correlation ID to each
        incoming request.

        Request bodies, authorization data and query
        values are intentionally not written to logs.
        """

        request_id = uuid4().hex

        request.state.request_id = (
            request_id
        )

        started_at = perf_counter()

        response = await call_next(
            request
        )

        duration_ms = (
            perf_counter()
            - started_at
        ) * 1000

        response.headers[
            "X-Request-ID"
        ] = request_id

        logger.info(
            (
                "API request completed | "
                "request_id=%s method=%s "
                "path=%s status=%s "
                "duration_ms=%.2f"
            ),
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        return response

    # --------------------------------------------------------
    # ROUTES
    # --------------------------------------------------------

    application.include_router(
        health_router
    )

    application.include_router(
        agent_router
    )

    return application


app = create_app()