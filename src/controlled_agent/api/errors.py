from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse


logger = logging.getLogger(
    "controlled_agent.api.errors"
)


# ============================================================
# REQUEST ID
# ============================================================

def get_request_id(
    request: Request,
) -> str:
    """
    Return the request correlation ID.

    A fallback ID is generated only if an exception
    occurred before normal request middleware could
    attach one.
    """

    request_id = getattr(
        request.state,
        "request_id",
        None,
    )

    if request_id:
        return str(
            request_id
        )

    return uuid4().hex


# ============================================================
# UNHANDLED ERRORS
# ============================================================

async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Handle unexpected server-side exceptions.

    Security rules:

    - Never expose exception text to clients.
    - Never expose stack traces to clients.
    - Keep traceback information in server logs.
    - Return a correlation ID for investigation.
    """

    request_id = get_request_id(
        request
    )

    logger.error(
        (
            "Unhandled API exception | "
            "request_id=%s method=%s path=%s"
        ),
        request_id,
        request.method,
        request.url.path,
        exc_info=(
            type(exc),
            exc,
            exc.__traceback__,
        ),
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": (
                "Internal server error."
            ),
            "request_id": request_id,
        },
        headers={
            "X-Request-ID": request_id,
        },
    )