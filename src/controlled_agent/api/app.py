from __future__ import annotations

from fastapi import FastAPI

from controlled_agent import __version__
from controlled_agent.api.config import (
    get_settings,
)
from controlled_agent.api.errors import (
    unhandled_exception_handler,
)
from controlled_agent.api.routes import (
    agent_router,
    health_router,
)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """

    settings = get_settings()

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

    application.add_exception_handler(
        Exception,
        unhandled_exception_handler,
    )

    application.include_router(
        health_router
    )

    application.include_router(
        agent_router
    )

    return application


app = create_app()