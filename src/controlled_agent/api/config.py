from __future__ import annotations

import os
from dataclasses import dataclass


# ============================================================
# SETTINGS
# ============================================================

@dataclass(frozen=True)
class ApiSettings:
    app_name: str = "Controlled Order Agent API"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"


# ============================================================
# HELPERS
# ============================================================

def _parse_bool(
    value: str,
) -> bool:
    return (
        value.strip().lower()
        in {
            "1",
            "true",
            "yes",
            "on",
        }
    )


def _resolve_log_level(
    value: str,
) -> str:
    normalized = (
        value.strip().upper()
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
# PUBLIC SETTINGS
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

    debug_requested = _parse_bool(
        os.getenv(
            "CONTROLLED_AGENT_DEBUG",
            "false",
        )
    )

    # Never expose FastAPI/Starlette debug
    # tracebacks in production.
    debug = (
        debug_requested
        and environment != "production"
    )

    log_level = _resolve_log_level(
        os.getenv(
            "CONTROLLED_AGENT_LOG_LEVEL",
            "INFO",
        )
    )

    return ApiSettings(
        environment=environment,
        debug=debug,
        log_level=log_level,
    )