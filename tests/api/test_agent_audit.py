from fastapi.testclient import TestClient

from controlled_agent.api import create_app
from controlled_agent.api.dependencies import (
    build_agent,
    build_audit_repository,
    get_agent,
    get_audit_repository,
)


def create_test_client(
    tmp_path,
) -> TestClient:
    app = create_app()

    database_path = (
        tmp_path
        / "agent-audit.db"
    )

    def override_get_agent():
        return build_agent(
            database_path
        )

    def override_get_audit_repository():
        return build_audit_repository(
            database_path
        )

    app.dependency_overrides[
        get_agent
    ] = override_get_agent

    app.dependency_overrides[
        get_audit_repository
    ] = override_get_audit_repository

    return TestClient(
        app
    )


def test_get_agent_run_audit(
    tmp_path,
):
    client = create_test_client(
        tmp_path
    )

    created = client.post(
        "/agent/runs",
        json={
            "message": "Check order 45821.",
        },
    )

    assert created.status_code == 201

    run_id = created.json()[
        "run_id"
    ]

    response = client.get(
        f"/agent/runs/{run_id}/audit"
    )

    assert response.status_code == 200

    events = response.json()

    assert len(events) > 0

    for event in events:
        assert set(event) == {
            "timestamp",
            "step",
            "event",
            "detail",
        }

    event_names = [
        item["event"]
        for item in events
    ]

    assert "request_received" in event_names


def test_unknown_run_audit_returns_404(
    tmp_path,
):
    client = create_test_client(
        tmp_path
    )

    response = client.get(
        "/agent/runs/missing-run/audit"
    )

    assert response.status_code == 404