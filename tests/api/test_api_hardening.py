from fastapi.testclient import TestClient

from controlled_agent.api import create_app
from controlled_agent.api.config import (
    get_settings,
)


def test_readiness_endpoint():
    app = create_app()
    client = TestClient(app)

    response = client.get(
        "/ready"
    )

    assert response.status_code == 200

    assert response.json() == {
        "ready": True,
        "service": "controlled-order-agent",
    }


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


def test_unknown_route_returns_404():
    app = create_app()
    client = TestClient(app)

    response = client.get(
        "/route-that-does-not-exist"
    )

    assert response.status_code == 404