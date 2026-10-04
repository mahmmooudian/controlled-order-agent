from fastapi.testclient import TestClient

from controlled_agent.api import create_app


def test_health_endpoint():
    app = create_app()

    client = TestClient(
        app
    )

    response = client.get(
        "/health"
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "ok"

    assert (
        payload["service"]
        == "controlled-order-agent"
    )

    assert "version" in payload