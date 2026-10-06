from __future__ import annotations

import os
from dataclasses import dataclass


# ============================================================
# API SETTINGS
# ============================================================

@dataclass(frozen=True)
class ApiSettings:
    app_name: str = (
        "Controlled Order Agent API"
    )

    environment: str = "development"

    debug: bool = False

    log_level: str = "INFO"

    allow_security_simulation: bool = False

    # --------------------------------------------------------
    # AUTHENTICATION / RBAC CREDENTIALS
    # --------------------------------------------------------

    # Backwards-compatible ADMIN credential.
    api_key: str | None = None

    # Read-only access.
    reader_api_key: str | None = None

    # Agent execution / continuation access.
    operator_api_key: str | None = None

    # Human approval access.
    approver_api_key: str | None = None


# ============================================================
# BOOLEAN PARSING
# ============================================================

def _parse_bool(
    value: str,
) -> bool:
    return (
        value
        .strip()
        .lower()
        in {
            "1",
            "true",
            "yes",
            "on",
        }
    )


# ============================================================
# LOG LEVEL
# ============================================================

def _resolve_log_level(
    value: str,
) -> str:
    normalized = (
        value
        .strip()
        .upper()
    )

    allowed = {
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    }

    if normalized not in allowed:
        return "INFO"

    return normalized


# ============================================================
# OPTIONAL SECRET
# ============================================================

def _resolve_optional_secret(
    value: str,
) -> str | None:
    normalized = value.strip()

    if not normalized:
        return None

    return normalized


# ============================================================
# SETTINGS FACTORY
# ============================================================

def get_settings() -> ApiSettings:
    environment = (
        os.getenv(
            "CONTROLLED_AGENT_ENV",
            "development",
        )
        .strip()
        .lower()
    )

    # --------------------------------------------------------
    # DEBUG
    # --------------------------------------------------------

    debug_requested = _parse_bool(
        os.getenv(
            "CONTROLLED_AGENT_DEBUG",
            "false",
        )
    )

    # Debug is never permitted in production.
    debug = (
        debug_requested
        and environment != "production"
    )

    # --------------------------------------------------------
    # LOGGING
    # --------------------------------------------------------

    log_level = _resolve_log_level(
        os.getenv(
            "CONTROLLED_AGENT_LOG_LEVEL",
            "INFO",
        )
    )

    # --------------------------------------------------------
    # SECURITY SIMULATION
    # --------------------------------------------------------

    simulation_requested = _parse_bool(
        os.getenv(
            (
                "CONTROLLED_AGENT_"
                "ALLOW_SECURITY_SIMULATION"
            ),
            "false",
        )
    )

    # Security simulations require explicit opt-in
    # and can never be enabled in production.
    allow_security_simulation = (
        simulation_requested
        and environment != "production"
    )

    # --------------------------------------------------------
    # ADMIN API KEY
    # --------------------------------------------------------

    api_key = _resolve_optional_secret(
        os.getenv(
            "CONTROLLED_AGENT_API_KEY",
            "",
        )
    )

    # --------------------------------------------------------
    # READER API KEY
    # --------------------------------------------------------

    reader_api_key = _resolve_optional_secret(
        os.getenv(
            "CONTROLLED_AGENT_READER_API_KEY",
            "",
        )
    )

    # --------------------------------------------------------
    # OPERATOR API KEY
    # --------------------------------------------------------

    operator_api_key = _resolve_optional_secret(
        os.getenv(
            "CONTROLLED_AGENT_OPERATOR_API_KEY",
            "",
        )
    )

    # --------------------------------------------------------
    # APPROVER API KEY
    # --------------------------------------------------------

    approver_api_key = _resolve_optional_secret(
        os.getenv(
            "CONTROLLED_AGENT_APPROVER_API_KEY",
            "",
        )
    )

    # --------------------------------------------------------
    # FINAL SETTINGS
    # --------------------------------------------------------

    return ApiSettings(
        environment=environment,
        debug=debug,
        log_level=log_level,
        allow_security_simulation=(
            allow_security_simulation
        ),
        api_key=api_key,
        reader_api_key=reader_api_key,
        operator_api_key=operator_api_key,
        approver_api_key=approver_api_key,
    )