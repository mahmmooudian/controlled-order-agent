from fastapi.testclient import TestClient

from controlled_agent.api import create_app
from controlled_agent.api.dependencies import (
    build_agent,
    get_agent,
)
from controlled_agent.domain.state import (
    AgentStatus,
)


def create_test_client(
    tmp_path,
) -> TestClient:
    """
    Every HTTP request receives a fresh
    Agent instance while all requests share
    the same temporary SQLite database.
    """

    app = create_app()

    database_path = (
        tmp_path
        / "agent-lifecycle.db"
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


def test_get_existing_agent_run(
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

    created_payload = (
        created.json()
    )

    run_id = (
        created_payload["run_id"]
    )

    response = client.get(
        f"/agent/runs/{run_id}"
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["run_id"] == run_id

    assert (
        payload["status"]
        == AgentStatus.DONE.value
    )

    assert payload["finished"] is True

    assert (
        payload["order_id"]
        == "45821"
    )


def test_get_unknown_run_returns_404(
    tmp_path,
):
    client = create_test_client(
        tmp_path
    )

    response = client.get(
        "/agent/runs/does-not-exist"
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Agent run not found."
    )


def test_continue_run_with_user_input(
    tmp_path,
):
    client = create_test_client(
        tmp_path
    )

    created = client.post(
        "/agent/runs",
        json={
            "message": "Where is my order?",
        },
    )

    assert created.status_code == 201

    created_payload = (
        created.json()
    )

    assert (
        created_payload["status"]
        == (
            AgentStatus
            .WAITING_FOR_INPUT
            .value
        )
    )

    run_id = (
        created_payload["run_id"]
    )

    response = client.post(
        f"/agent/runs/{run_id}/input",
        json={
            "message": "8452",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["run_id"] == run_id

    assert (
        payload["status"]
        == (
            AgentStatus
            .WAITING_FOR_APPROVAL
            .value
        )
    )

    assert (
        payload["awaiting_approval"]
        is True
    )

    assert payload["order_id"] == "8452"

    # Verify persistence through another HTTP request.
    restored = client.get(
        f"/agent/runs/{run_id}"
    )

    assert restored.status_code == 200

    assert (
        restored.json()["status"]
        == (
            AgentStatus
            .WAITING_FOR_APPROVAL
            .value
        )
    )


def test_approve_agent_run(
    tmp_path,
):
    client = create_test_client(
        tmp_path
    )

    created = client.post(
        "/agent/runs",
        json={
            "message": "Check order 8452.",
        },
    )

    assert created.status_code == 201

    run_id = (
        created.json()["run_id"]
    )

    response = client.post(
        f"/agent/runs/{run_id}/approval",
        json={
            "approved": True,
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["run_id"] == run_id

    assert (
        payload["status"]
        == AgentStatus.DONE.value
    )

    assert payload["finished"] is True

    assert (
        payload["awaiting_approval"]
        is False
    )

    assert payload["ticket_id"] is not None

    restored = client.get(
        f"/agent/runs/{run_id}"
    )

    assert restored.status_code == 200

    assert (
        restored.json()["ticket_id"]
        == payload["ticket_id"]
    )


def test_deny_agent_run(
    tmp_path,
):
    client = create_test_client(
        tmp_path
    )

    created = client.post(
        "/agent/runs",
        json={
            "message": "Check order 8452.",
        },
    )

    assert created.status_code == 201

    run_id = (
        created.json()["run_id"]
    )

    response = client.post(
        f"/agent/runs/{run_id}/approval",
        json={
            "approved": False,
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["run_id"] == run_id
    assert payload["finished"] is True

    assert (
        payload["awaiting_approval"]
        is False
    )

    assert payload["ticket_id"] is None


def test_invalid_run_transition_returns_conflict(
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

    run_id = (
        created.json()["run_id"]
    )

    # This run is already DONE, therefore it
    # must not accept extra conversation input.
    input_response = client.post(
        f"/agent/runs/{run_id}/input",
        json={
            "message": "8452",
        },
    )

    assert (
        input_response.status_code
        == 409
    )

    # Nor may a finished run accept a new
    # approval decision.
    approval_response = client.post(
        f"/agent/runs/{run_id}/approval",
        json={
            "approved": True,
        },
    )

    assert (
        approval_response.status_code
        == 409
    )