from fastapi.testclient import TestClient

from controlled_agent.api import create_app
from controlled_agent.api.dependencies import (
    build_agent,
    get_agent,
)


def create_test_client(
    tmp_path,
) -> TestClient:
    app = create_app()

    database_path = (
        tmp_path
        / "gui-compatibility.db"
    )

    def override_get_agent():
        return build_agent(
            database_path
        )

    app.dependency_overrides[
        get_agent
    ] = override_get_agent

    return TestClient(app)


def test_api_returns_human_approval_state(
    tmp_path,
):
    """
    The GUI displays human_approved explicitly,
    so the public API contract must preserve it.
    """

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

    created_payload = created.json()

    assert (
        created_payload["awaiting_approval"]
        is True
    )

    assert (
        created_payload["human_approved"]
        is None
    )

    run_id = created_payload["run_id"]

    approved = client.post(
        f"/agent/runs/{run_id}/approval",
        json={
            "approved": True,
        },
    )

    assert approved.status_code == 200

    approved_payload = approved.json()

    assert (
        approved_payload["human_approved"]
        is True
    )

    assert (
        approved_payload["awaiting_approval"]
        is False
    )

    assert approved_payload["ticket_id"] is not None


def test_injection_flag_reaches_agent_runtime(
    tmp_path,
):
    """
    Verify that the API security-demo flag is
    applied to the Runtime before execution.
    """

    app = create_app()

    database_path = (
        tmp_path
        / "gui-injection.db"
    )

    agent = build_agent(
        database_path
    )

    observed = {
        "simulate_lookup_injection": None,
    }

    original_run = agent.run

    def observed_run(
        message: str,
    ):
        observed[
            "simulate_lookup_injection"
        ] = (
            agent.simulate_lookup_injection
        )

        return original_run(
            message
        )

    agent.run = observed_run

    def override_get_agent():
        return agent

    app.dependency_overrides[
        get_agent
    ] = override_get_agent

    client = TestClient(app)

    response = client.post(
        "/agent/runs",
        json={
            "message": (
                "Check order 45821."
            ),
            "simulate_lookup_injection": True,
        },
    )

    assert response.status_code == 201

    assert (
        observed[
            "simulate_lookup_injection"
        ]
        is True
    )

    payload = response.json()

    assert payload["order_id"] == "45821"
    assert payload["ticket_id"] is None