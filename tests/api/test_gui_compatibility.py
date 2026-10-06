from fastapi.testclient import TestClient

from controlled_agent.api.app import (
    create_app,
)
from controlled_agent.api.config import (
    ApiSettings,
    get_settings,
)
from controlled_agent.api.dependencies import (
    build_agent,
    get_agent,
)


# ============================================================
# TEST CLIENT
# ============================================================

def create_test_client(
    tmp_path,
):
    """
    Create an isolated API client backed by
    a temporary persistent Agent database.
    """

    app = create_app()

    database_path = (
        tmp_path
        / "gui-compatibility.db"
    )

    agent = build_agent(
        database_path
    )

    def override_get_agent():
        return agent

    app.dependency_overrides[
        get_agent
    ] = override_get_agent

    client = TestClient(
        app
    )

    return (
        client,
        agent,
    )


# ============================================================
# HUMAN APPROVAL STATE
# ============================================================

def test_api_returns_human_approval_state(
    tmp_path,
):
    """
    Verify that the public API contract exposes
    the Human Approval state required by the GUI.
    """

    (
        client,
        _,
    ) = create_test_client(
        tmp_path
    )

    # --------------------------------------------------------
    # CREATE DELAYED ORDER RUN
    # --------------------------------------------------------

    response = client.post(
        "/agent/runs",
        json={
            "message": (
                "Check order 8452."
            ),
        },
    )

    assert (
        response.status_code
        == 201
    )

    payload = response.json()

    run_id = payload[
        "run_id"
    ]

    assert (
        payload[
            "awaiting_approval"
        ]
        is True
    )

    assert (
        payload[
            "human_approved"
        ]
        is None
    )

    assert (
        payload[
            "ticket_id"
        ]
        is None
    )

    # --------------------------------------------------------
    # APPROVE WRITE ACTION
    # --------------------------------------------------------

    approval_response = client.post(
        (
            f"/agent/runs/"
            f"{run_id}/approval"
        ),
        json={
            "approved": True,
        },
    )

    assert (
        approval_response.status_code
        == 200
    )

    approved_payload = (
        approval_response.json()
    )

    assert (
        approved_payload[
            "human_approved"
        ]
        is True
    )

    assert (
        approved_payload[
            "awaiting_approval"
        ]
        is False
    )

    assert (
        approved_payload[
            "ticket_id"
        ]
        is not None
    )


# ============================================================
# SECURITY DEMO FLAG
# ============================================================

def test_injection_flag_reaches_agent_runtime(
    tmp_path,
):
    """
    Verify that the API security-demo flag is
    applied to the Runtime before execution,
    but only when the server explicitly enables
    security simulations in development.
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
            agent
            .simulate_lookup_injection
        )

        return original_run(
            message
        )

    agent.run = observed_run

    # --------------------------------------------------------
    # AGENT DEPENDENCY
    # --------------------------------------------------------

    def override_get_agent():
        return agent

    app.dependency_overrides[
        get_agent
    ] = override_get_agent

    # --------------------------------------------------------
    # SECURITY SETTINGS DEPENDENCY
    # --------------------------------------------------------

    def override_get_settings():
        return ApiSettings(
            environment="development",
            allow_security_simulation=True,
        )

    app.dependency_overrides[
        get_settings
    ] = override_get_settings

    # --------------------------------------------------------
    # API REQUEST
    # --------------------------------------------------------

    client = TestClient(
        app
    )

    response = client.post(
        "/agent/runs",
        json={
            "message": (
                "Check order 45821."
            ),
            "simulate_lookup_injection": True,
        },
    )

    # --------------------------------------------------------
    # ASSERTIONS
    # --------------------------------------------------------

    assert (
        response.status_code
        == 201
    )

    assert (
        observed[
            "simulate_lookup_injection"
        ]
        is True
    )

    payload = response.json()

    assert (
        payload[
            "order_id"
        ]
        == "45821"
    )

    # Prompt Injection embedded in tool output
    # must never cause an unauthorized WRITE.
    assert (
        payload[
            "ticket_id"
        ]
        is None
    )