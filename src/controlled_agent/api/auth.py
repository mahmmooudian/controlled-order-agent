from __future__ import annotations

import secrets

from fastapi import (
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from controlled_agent.api.config import (
    ApiSettings,
    get_settings,
)


bearer_scheme = HTTPBearer(
    auto_error=False,
)


def _unauthorized() -> HTTPException:
    """
    Return one generic authentication error.

    The response intentionally does not reveal
    whether the API key is missing, incorrect,
    or not configured on the server.
    """

    return HTTPException(
        status_code=(
            status.HTTP_401_UNAUTHORIZED
        ),
        detail=(
            "Invalid or missing API credentials."
        ),
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


def require_api_key(
    credentials: (
        HTTPAuthorizationCredentials
        | None
    ) = Depends(
        bearer_scheme
    ),
    settings: ApiSettings = Depends(
        get_settings
    ),
) -> None:
    """
    Protect sensitive Agent API endpoints.

    Production behavior is fail-closed:
    if no server API key exists, requests
    cannot be authenticated.

    Development remains backward-compatible:
    when no API key is configured, authentication
    is not required.

    If a key is configured in any environment,
    Bearer authentication is enforced.
    """

    expected_key = settings.api_key

    # Development-only compatibility mode.
    if (
        settings.environment
        != "production"
        and expected_key is None
    ):
        return

    # Production without a configured key
    # must fail closed.
    if expected_key is None:
        raise _unauthorized()

    if credentials is None:
        raise _unauthorized()

    if (
        credentials.scheme.lower()
        != "bearer"
    ):
        raise _unauthorized()

    provided_key = (
        credentials.credentials
    )

    if not secrets.compare_digest(
        provided_key,
        expected_key,
    ):
        raise _unauthorized()