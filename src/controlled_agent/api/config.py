from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ApiSettings:
    app_name: str = "Controlled Order Agent API"
    environment: str = "development"
    debug: bool = False


def get_settings() -> ApiSettings:
    environment = os.getenv(
        "CONTROLLED_AGENT_ENV",
        "development",
    )

    debug_raw = os.getenv(
        "CONTROLLED_AGENT_DEBUG",
        "false",
    )

    debug = (
        debug_raw.strip().lower()
        in {
            "1",
            "true",
            "yes",
            "on",
        }
    )

    return ApiSettings(
        environment=environment,
        debug=debug,
    )