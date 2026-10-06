from __future__ import annotations

import secrets
from dataclasses import dataclass
from enum import Enum
from typing import Callable

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


# ============================================================
# ROLES
# ============================================================

class ApiRole(str, Enum):
    READER = "reader"
    OPERATOR = "operator"
    APPROVER = "approver"
    ADMIN = "admin"


@dataclass(frozen=True)
class ApiPrincipal:
    role: ApiRole


# ============================================================
# HTTP BEARER
# ============================================================

bearer_scheme = HTTPBearer(
    auto_error=False,
)


# ============================================================
# AUTHENTICATION / AUTHORIZATION ERRORS
# ============================================================

def _unauthorized() -> HTTPException:
    """
    Return one generic authentication error.

    The response intentionally does not reveal
    whether credentials are missing, incorrect,
    or the server is misconfigured.
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


def _forbidden() -> HTTPException:
    """
    Return a generic authorization failure.
    """

    return HTTPException(
        status_code=(
            status.HTTP_403_FORBIDDEN
        ),
        detail=(
            "Insufficient API permissions."
        ),
    )


# ============================================================
# CONFIGURED CREDENTIALS
# ============================================================

def _configured_credentials(
    settings: ApiSettings,
) -> tuple[
    tuple[ApiRole, str],
    ...,
]:
    """
    Return configured role credentials.

    CONTROLLED_AGENT_API_KEY remains the
    backwards-compatible administrator key.
    """

    credentials: list[
        tuple[ApiRole, str]
    ] = []

    if settings.api_key is not None:
        credentials.append(
            (
                ApiRole.ADMIN,
                settings.api_key,
            )
        )

    if settings.approver_api_key is not None:
        credentials.append(
            (
                ApiRole.APPROVER,
                settings.approver_api_key,
            )
        )

    if settings.operator_api_key is not None:
        credentials.append(
            (
                ApiRole.OPERATOR,
                settings.operator_api_key,
            )
        )

    if settings.reader_api_key is not None:
        credentials.append(
            (
                ApiRole.READER,
                settings.reader_api_key,
            )
        )

    return tuple(credentials)


# ============================================================
# AUTHENTICATION
# ============================================================

def authenticate_api_key(
    credentials: (
        HTTPAuthorizationCredentials
        | None
    ) = Depends(
        bearer_scheme
    ),
    settings: ApiSettings = Depends(
        get_settings
    ),
) -> ApiPrincipal:
    """
    Authenticate a Bearer credential and resolve
    it to one API role.

    Production is fail-closed.

    Development remains backwards-compatible:
    when no credentials of any role are configured,
    requests receive temporary ADMIN authority.
    """

    configured = (
        _configured_credentials(
            settings
        )
    )

    # --------------------------------------------------------
    # DEVELOPMENT COMPATIBILITY MODE
    # --------------------------------------------------------

    if (
        settings.environment
        != "production"
        and not configured
    ):
        return ApiPrincipal(
            role=ApiRole.ADMIN
        )

    # --------------------------------------------------------
    # PRODUCTION FAIL-CLOSED
    # --------------------------------------------------------

    if not configured:
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

    # --------------------------------------------------------
    # CONSTANT-TIME KEY COMPARISON
    # --------------------------------------------------------

    for role, expected_key in configured:

        if secrets.compare_digest(
            provided_key,
            expected_key,
        ):
            return ApiPrincipal(
                role=role
            )

    raise _unauthorized()


# ============================================================
# BACKWARDS-COMPATIBLE AUTH DEPENDENCY
# ============================================================

def require_api_key(
    principal: ApiPrincipal = Depends(
        authenticate_api_key
    ),
) -> None:
    """
    Preserve the 5.5A authentication dependency.

    New code should prefer role-based dependencies.
    """

    del principal


# ============================================================
# ROLE AUTHORIZATION
# ============================================================

def require_roles(
    *allowed_roles: ApiRole,
) -> Callable[..., ApiPrincipal]:
    """
    Build a FastAPI dependency that requires
    one of the supplied roles.
    """

    allowed = frozenset(
        allowed_roles
    )

    if not allowed:
        raise ValueError(
            "At least one API role is required."
        )

    def dependency(
        principal: ApiPrincipal = Depends(
            authenticate_api_key
        ),
    ) -> ApiPrincipal:

        if principal.role not in allowed:
            raise _forbidden()

        return principal

    return dependency


# ============================================================
# ROUTE-SPECIFIC AUTHORIZATION DEPENDENCIES
# ============================================================

require_run_reader = require_roles(
    ApiRole.READER,
    ApiRole.OPERATOR,
    ApiRole.APPROVER,
    ApiRole.ADMIN,
)

require_run_operator = require_roles(
    ApiRole.OPERATOR,
    ApiRole.ADMIN,
)

require_run_approver = require_roles(
    ApiRole.APPROVER,
    ApiRole.ADMIN,
)

require_audit_reader = require_roles(
    ApiRole.READER,
    ApiRole.ADMIN,
)