import logging
import re

from fastapi.testclient import (
    TestClient,
)

from controlled_agent.api import (
    create_app,
)
from controlled_agent.api.config import (
    get_settings,
)


REQUEST_ID_PATTERN = re.compile(
    r"^[0-9a-f]{32}$"
)


# ============================================================
# READINESS
# ============================================================

def test_readiness_endpoint():
    app = create_app()

    client = TestClient(
        app
    )

    response = client.get(
        "/ready"
    )

    assert response.status_code == 200

    assert response.json() == {
        "ready": True,
        "service": "controlled-order-agent",
    }

    request_id = response.headers[
        "X-Request-ID"
    ]

    assert REQUEST_ID_PATTERN.fullmatch(
        request_id
    )


# ============================================================
# DEFAULT SETTINGS
# ============================================================

def test_default_api_settings():
    settings = get_settings()

    assert (
        settings.app_name
        == "Controlled Order Agent API"
    )

    assert settings.environment

    assert isinstance(
        settings.debug,
        bool,
    )

    assert settings.log_level in {
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    }


# ============================================================
# PRODUCTION DEBUG SAFETY
# ============================================================

def test_debug_is_forced_off_in_production(
    monkeypatch,
):
    monkeypatch.setenv(
        "CONTROLLED_AGENT_ENV",
        "production",
    )

    monkeypatch.setenv(
        "CONTROLLED_AGENT_DEBUG",
        "true",
    )

    settings = get_settings()

    assert (
        settings.environment
        == "production"
    )

    assert settings.debug is False


# ============================================================
# SUCCESSFUL REQUEST CORRELATION
# ============================================================

def test_success_response_has_request_id():
    app = create_app()

    client = TestClient(
        app
    )

    response = client.get(
        "/health"
    )

    assert response.status_code == 200

    request_id = response.headers[
        "X-Request-ID"
    ]

    assert REQUEST_ID_PATTERN.fullmatch(
        request_id
    )


# ============================================================
# NORMAL HTTP ERRORS MUST REMAIN NORMAL
# ============================================================

def test_unknown_route_returns_404_with_request_id():
    app = create_app()

    client = TestClient(
        app
    )

    response = client.get(
        "/route-that-does-not-exist"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Not Found",
    }

    request_id = response.headers[
        "X-Request-ID"
    ]

    assert REQUEST_ID_PATTERN.fullmatch(
        request_id
    )


# ============================================================
# SAFE INTERNAL SERVER ERROR
# ============================================================

def test_unhandled_exception_is_safe_and_correlated(
    caplog,
):
    app = create_app()

    secret_internal_message = (
        "SECRET_DATABASE_PASSWORD_123"
    )

    @app.get(
        "/test/internal-error"
    )
    def force_internal_error():
        raise RuntimeError(
            secret_internal_message
        )

    client = TestClient(
        app,
        raise_server_exceptions=False,
    )

    with caplog.at_level(
        logging.ERROR,
        logger=(
            "controlled_agent.api.errors"
        ),
    ):
        response = client.get(
            "/test/internal-error"
        )

    assert response.status_code == 500

    payload = response.json()

    assert (
        payload["detail"]
        == "Internal server error."
    )

    request_id = payload[
        "request_id"
    ]

    assert REQUEST_ID_PATTERN.fullmatch(
        request_id
    )

    assert (
        response.headers[
            "X-Request-ID"
        ]
        == request_id
    )

    # Internal exception data must never
    # appear in the client response.
    assert (
        secret_internal_message
        not in response.text
    )

    # The server log must contain enough
    # information to correlate the failure.
    assert request_id in caplog.text

    assert (
        "Unhandled API exception"
        in caplog.text
    )

    # Detailed exception information is allowed
    # only in the server-side diagnostic log.
    assert (
        secret_internal_message
        in caplog.text
    )