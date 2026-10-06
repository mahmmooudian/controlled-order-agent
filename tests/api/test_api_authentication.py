from fastapi.testclient import (
    TestClient,
)

from controlled_agent.api.app import (
    create_app,
)
from controlled_agent.api.dependencies import (
    build_agent,
    get_agent,
)


def create_test_client(
    tmp_path,
):
    app = create_app()

    agent = build_agent(
        tmp_path
        / "authentication.db"
    )

    def override_get_agent():
        return agent

    app.dependency_overrides[
        get_agent
    ] = override_get_agent

    return TestClient(
        app
    )


def test_health_remains_public_in_production(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "CONTROLLED_AGENT_ENV",
        "production",
    )

    monkeypatch.delenv(
        "CONTROLLED_AGENT_API_KEY",
        raising=False,
    )

    client = create_test_client(
        tmp_path
    )

    response = client.get(
        "/health"
    )

    assert response.status_code == 200


def test_production_agent_api_fails_closed_without_server_key(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "CONTROLLED_AGENT_ENV",
        "production",
    )

    monkeypatch.delenv(
        "CONTROLLED_AGENT_API_KEY",
        raising=False,
    )

    client = create_test_client(
        tmp_path
    )

    response = client.post(
        "/agent/runs",
        json={
            "message": (
                "Check order 45821."
            ),
        },
    )

    assert response.status_code == 401

    assert (
        response.json()["detail"]
        == (
            "Invalid or missing "
            "API credentials."
        )
    )

    assert (
        response.headers[
            "www-authenticate"
        ]
        == "Bearer"
    )


def test_agent_api_rejects_missing_bearer_token(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "CONTROLLED_AGENT_ENV",
        "production",
    )

    monkeypatch.setenv(
        "CONTROLLED_AGENT_API_KEY",
        "server-secret-key",
    )

    client = create_test_client(
        tmp_path
    )

    response = client.post(
        "/agent/runs",
        json={
            "message": (
                "Check order 45821."
            ),
        },
    )

    assert response.status_code == 401


def test_agent_api_rejects_wrong_bearer_token(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "CONTROLLED_AGENT_ENV",
        "production",
    )

    monkeypatch.setenv(
        "CONTROLLED_AGENT_API_KEY",
        "server-secret-key",
    )

    client = create_test_client(
        tmp_path
    )

    response = client.post(
        "/agent/runs",
        headers={
            "Authorization": (
                "Bearer wrong-secret"
            ),
        },
        json={
            "message": (
                "Check order 45821."
            ),
        },
    )

    assert response.status_code == 401


def test_agent_api_accepts_correct_bearer_token(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "CONTROLLED_AGENT_ENV",
        "production",
    )

    monkeypatch.setenv(
        "CONTROLLED_AGENT_API_KEY",
        "server-secret-key",
    )

    client = create_test_client(
        tmp_path
    )

    response = client.post(
        "/agent/runs",
        headers={
            "Authorization": (
                "Bearer server-secret-key"
            ),
        },
        json={
            "message": (
                "Check order 45821."
            ),
        },
    )

    assert response.status_code == 201

    assert (
        response.json()["order_id"]
        == "45821"
    )


def test_development_without_api_key_remains_compatible(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "CONTROLLED_AGENT_ENV",
        "development",
    )

    monkeypatch.delenv(
        "CONTROLLED_AGENT_API_KEY",
        raising=False,
    )

    client = create_test_client(
        tmp_path
    )

    response = client.post(
        "/agent/runs",
        json={
            "message": (
                "Check order 45821."
            ),
        },
    )

    assert response.status_code == 201