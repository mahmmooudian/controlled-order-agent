from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Return a stable public error response.

    Internal exception details are intentionally
    not exposed to API clients.
    """

    return JSONResponse(
        status_code=500,
        content={
            "detail": (
                "Internal server error."
            ),
        },
    )