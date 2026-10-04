from __future__ import annotations

from fastapi import FastAPI

from controlled_agent import __version__
from controlled_agent.api.routes import health_router


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """

    application = FastAPI(
        title="Controlled Order Agent API",
        description=(
            "Policy-controlled AI Agent backend "
            "for safe order tracking and "
            "human-approved actions."
        ),
        version=__version__,
    )

    application.include_router(
        health_router
    )

    return application


app = create_app()
