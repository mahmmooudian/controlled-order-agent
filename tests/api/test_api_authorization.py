from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from controlled_agent.api.config import (
    ApiSettings,
    get_settings,
)
from controlled_agent.api.dependencies import (
    get_agent,
    get_audit_repository,
)
from controlled_agent.api.routes.agent import router
from controlled_agent.domain.state import (
    AgentStatus,
)


# ============================================================
# TEST CREDENTIALS
# ============================================================

ADMIN_KEY = "test-admin-key"
READER_KEY = "test-reader-key"
OPERATOR_KEY = "test-operator-key"
APPROVER_KEY = "test-approver-key"


def auth_headers(
    api_key: str,
) -> dict[str, str]:
    return {
        "Authorization": (
            f"Bearer {api_key}"
        )
    }


# ============================================================
# FAKE STATE
# ============================================================

def make_state(
    *,
    status: AgentStatus = AgentStatus.DONE,
    order_id: str = "45821",
    days_delayed: int = 2,
    awaiting_user_input: bool = False,
    awaiting_approval: bool = False,
    human_approved: bool | None = None,
):
    return SimpleNamespace(
        user_message="Test request.",
        latest_user_message="Test request.",
        order_id=order_id,
        order_status=None,
        days_delayed=days_delayed,
        awaiting_approval=awaiting_approval,
        human_approved=human_approved,
        ticket_id=None,
        steps=1,
        status=status,
        finished=(
            status == AgentStatus.DONE
        ),
        awaiting_user_input=(
            awaiting_user_input
        ),
        final_message="Test response.",
    )


# ============================================================
# FAKE AGENT
# ============================================================

class FakeAgent:
    def __init__(
        self,
    ) -> None:
        self.current_run_id: str | None = None

        self.simulate_lookup_injection = False

        self.states = {
            "run-123": make_state(),
            "input-run": make_state(
                status=(
                    AgentStatus.WAITING_FOR_INPUT
                ),
                awaiting_user_input=True,
            ),
            "approval-run": make_state(
                status=(
                    AgentStatus.WAITING_FOR_APPROVAL
                ),
                order_id="8452",
                days_delayed=5,
                awaiting_approval=True,
            ),
        }

    def run(
        self,
        message: str,
    ):
        self.current_run_id = (
            "created-run"
        )

        state = make_state()

        self.states[
            self.current_run_id
        ] = state

        return state

    def load_run(
        self,
        run_id: str,
    ):
        return self.states.get(
            run_id
        )

    def resume_with_user_input(
        self,
        state,
        message: str,
    ):
        state.latest_user_message = (
            message
        )

        state.status = AgentStatus.DONE
        state.finished = True
        state.awaiting_user_input = False
        state.final_message = (
            "Input accepted."
        )

        return state

    def resume_with_approval(
        self,
        state,
        approved: bool,
    ):
        state.human_approved = approved
        state.awaiting_approval = False
        state.status = AgentStatus.DONE
        state.finished = True
        state.final_message = (
            "Approval processed."
        )

        return state


# ============================================================
# FAKE AUDIT REPOSITORY
# ============================================================

class FakeAuditRepository:
    def get_for_run(
        self,
        run_id: str,
    ):
        return []


# ============================================================
# TEST CLIENT
# ============================================================

def create_rbac_client():
    app = FastAPI()

    app.include_router(
        router
    )

    fake_agent = FakeAgent()

    fake_audit_repository = (
        FakeAuditRepository()
    )

    settings = ApiSettings(
        environment="production",
        api_key=ADMIN_KEY,
        reader_api_key=READER_KEY,
        operator_api_key=OPERATOR_KEY,
        approver_api_key=APPROVER_KEY,
    )

    app.dependency_overrides[
        get_settings
    ] = lambda: settings

    app.dependency_overrides[
        get_agent
    ] = lambda: fake_agent

    app.dependency_overrides[
        get_audit_repository
    ] = lambda: (
        fake_audit_repository
    )

    client = TestClient(
        app
    )

    return (
        client,
        fake_agent,
    )


# ============================================================
# CREATE RUN AUTHORIZATION
# ============================================================

@pytest.mark.parametrize(
    "api_key",
    [
        READER_KEY,
        APPROVER_KEY,
    ],
)
def test_non_operator_roles_cannot_create_run(
    api_key: str,
):
    client, _ = create_rbac_client()

    response = client.post(
        "/agent/runs",
        headers=auth_headers(
            api_key
        ),
        json={
            "message": (
                "Check order 45821."
            ),
        },
    )

    assert response.status_code == 403

    assert response.json() == {
        "detail": (
            "Insufficient API permissions."
        )
    }


def test_operator_can_create_run():
    client, _ = create_rbac_client()

    response = client.post(
        "/agent/runs",
        headers=auth_headers(
            OPERATOR_KEY
        ),
        json={
            "message": (
                "Check order 45821."
            ),
        },
    )

    assert response.status_code == 201

    assert (
        response.json()["run_id"]
        == "created-run"
    )


def test_admin_can_create_run():
    client, _ = create_rbac_client()

    response = client.post(
        "/agent/runs",
        headers=auth_headers(
            ADMIN_KEY
        ),
        json={
            "message": (
                "Check order 45821."
            ),
        },
    )

    assert response.status_code == 201


# ============================================================
# READ RUN AUTHORIZATION
# ============================================================

@pytest.mark.parametrize(
    "api_key",
    [
        READER_KEY,
        OPERATOR_KEY,
        APPROVER_KEY,
        ADMIN_KEY,
    ],
)
def test_authorized_roles_can_read_run(
    api_key: str,
):
    client, _ = create_rbac_client()

    response = client.get(
        "/agent/runs/run-123",
        headers=auth_headers(
            api_key
        ),
    )

    assert response.status_code == 200

    assert (
        response.json()["run_id"]
        == "run-123"
    )


# ============================================================
# CONTINUE RUN AUTHORIZATION
# ============================================================

def test_operator_can_continue_run():
    client, _ = create_rbac_client()

    response = client.post(
        "/agent/runs/input-run/input",
        headers=auth_headers(
            OPERATOR_KEY
        ),
        json={
            "message": "45821",
        },
    )

    assert response.status_code == 200

    assert (
        response.json()[
            "awaiting_user_input"
        ]
        is False
    )


def test_reader_cannot_continue_run():
    client, _ = create_rbac_client()

    response = client.post(
        "/agent/runs/input-run/input",
        headers=auth_headers(
            READER_KEY
        ),
        json={
            "message": "45821",
        },
    )

    assert response.status_code == 403


def test_approver_cannot_continue_run():
    client, _ = create_rbac_client()

    response = client.post(
        "/agent/runs/input-run/input",
        headers=auth_headers(
            APPROVER_KEY
        ),
        json={
            "message": "45821",
        },
    )

    assert response.status_code == 403


# ============================================================
# APPROVAL AUTHORIZATION
# ============================================================

def test_approver_can_approve_run():
    client, _ = create_rbac_client()

    response = client.post(
        "/agent/runs/approval-run/approval",
        headers=auth_headers(
            APPROVER_KEY
        ),
        json={
            "approved": True,
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert (
        payload["human_approved"]
        is True
    )

    assert (
        payload["awaiting_approval"]
        is False
    )


@pytest.mark.parametrize(
    "api_key",
    [
        READER_KEY,
        OPERATOR_KEY,
    ],
)
def test_non_approver_roles_cannot_approve(
    api_key: str,
):
    client, _ = create_rbac_client()

    response = client.post(
        "/agent/runs/approval-run/approval",
        headers=auth_headers(
            api_key
        ),
        json={
            "approved": True,
        },
    )

    assert response.status_code == 403

    assert response.json() == {
        "detail": (
            "Insufficient API permissions."
        )
    }


def test_admin_can_approve_run():
    client, _ = create_rbac_client()

    response = client.post(
        "/agent/runs/approval-run/approval",
        headers=auth_headers(
            ADMIN_KEY
        ),
        json={
            "approved": True,
        },
    )

    assert response.status_code == 200


# ============================================================
# AUDIT AUTHORIZATION
# ============================================================

def test_reader_can_read_audit():
    client, _ = create_rbac_client()

    response = client.get(
        "/agent/runs/run-123/audit",
        headers=auth_headers(
            READER_KEY
        ),
    )

    assert response.status_code == 200
    assert response.json() == []


def test_admin_can_read_audit():
    client, _ = create_rbac_client()

    response = client.get(
        "/agent/runs/run-123/audit",
        headers=auth_headers(
            ADMIN_KEY
        ),
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "api_key",
    [
        OPERATOR_KEY,
        APPROVER_KEY,
    ],
)
def test_non_audit_roles_cannot_read_audit(
    api_key: str,
):
    client, _ = create_rbac_client()

    response = client.get(
        "/agent/runs/run-123/audit",
        headers=auth_headers(
            api_key
        ),
    )

    assert response.status_code == 403


# ============================================================
# AUTHENTICATION STILL PRECEDES AUTHORIZATION
# ============================================================

def test_missing_credentials_returns_401():
    client, _ = create_rbac_client()

    response = client.get(
        "/agent/runs/run-123",
    )

    assert response.status_code == 401


def test_unknown_credentials_returns_401():
    client, _ = create_rbac_client()

    response = client.get(
        "/agent/runs/run-123",
        headers=auth_headers(
            "unknown-key"
        ),
    )

    assert response.status_code == 401