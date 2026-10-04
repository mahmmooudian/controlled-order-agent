from fastapi.testclient import TestClient

from controlled_agent.api import create_app
from controlled_agent.api.dependencies import (
    build_agent,
    get_agent,
)
from controlled_agent.domain.state import AgentStatus


def create_test_client(
    tmp_path,
) -> TestClient:
    """
    Create an isolated API client backed by
    a temporary SQLite database.
    """

    app = create_app()

    database_path = (
        tmp_path
        / "controlled-agent-api.db"
    )

    def override_get_agent():
        return build_agent(
            database_path
        )

    app.dependency_overrides[
        get_agent
    ] = override_get_agent

    return TestClient(
        app
    )


def test_create_completed_agent_run(
    tmp_path,
):
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

    payload = response.json()

    assert payload["run_id"]

    assert (
        payload["status"]
        == AgentStatus.DONE.value
    )

    assert payload["finished"] is True

    assert (
        payload["awaiting_user_input"]
        is False
    )

    assert (
        payload["awaiting_approval"]
        is False
    )

    assert (
        payload["order_id"]
        == "45821"
    )

    assert (
        payload["order_status"]
        == "shipped"
    )

    assert (
        payload["days_delayed"]
        == 2
    )

    assert payload["ticket_id"] is None

    assert (
        payload["final_message"]
        is not None
    )


def test_create_agent_run_waiting_for_approval(
    tmp_path,
):
    client = create_test_client(
        tmp_path
    )

    response = client.post(
        "/agent/runs",
        json={
            "message": (
                "Check order 8452."
            ),
        },
    )

    assert response.status_code == 201

    payload = response.json()

    assert payload["run_id"]

    assert (
        payload["status"]
        == (
            AgentStatus
            .WAITING_FOR_APPROVAL
            .value
        )
    )

    assert payload["finished"] is False

    assert (
        payload["awaiting_approval"]
        is True
    )

    assert (
        payload["order_id"]
        == "8452"
    )

    assert (
        payload["order_status"]
        == "delayed"
    )

    assert (
        payload["days_delayed"]
        == 5
    )

    assert payload["ticket_id"] is None


def test_create_agent_run_rejects_invalid_request(
    tmp_path,
):
    client = create_test_client(
        tmp_path
    )

    empty_message = client.post(
        "/agent/runs",
        json={
            "message": "",
        },
    )

    assert (
        empty_message.status_code
        == 422
    )

    missing_message = client.post(
        "/agent/runs",
        json={},
    )

    assert (
        missing_message.status_code
        == 422
    )

    extra_field = client.post(
        "/agent/runs",
        json={
            "message": "Check order 45821.",
            "unsafe_extra": True,
        },
    )

    assert (
        extra_field.status_code
        == 422
    )