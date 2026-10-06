import pytest
from fastapi import HTTPException

from controlled_agent.api.config import (
    ApiSettings,
    get_settings,
)
from controlled_agent.api.routes.agent import (
    create_agent_run,
)
from controlled_agent.api.schemas import (
    CreateAgentRunRequest,
)
from controlled_agent.domain.state import (
    AgentState,
)


class FakeAgent:
    def __init__(self):
        self.simulate_lookup_injection = False
        self.current_run_id = "run-test"
        self.run_called = False

    def run(
        self,
        message: str,
    ) -> AgentState:
        self.run_called = True

        return AgentState(
            user_message=message,
            latest_user_message=message,
        )


def test_security_simulation_disabled_by_default(
    monkeypatch,
):
    monkeypatch.delenv(
        "CONTROLLED_AGENT_ALLOW_SECURITY_SIMULATION",
        raising=False,
    )

    monkeypatch.setenv(
        "CONTROLLED_AGENT_ENV",
        "development",
    )

    settings = get_settings()

    assert (
        settings.allow_security_simulation
        is False
    )


def test_security_simulation_can_be_enabled_in_development(
    monkeypatch,
):
    monkeypatch.setenv(
        "CONTROLLED_AGENT_ENV",
        "development",
    )

    monkeypatch.setenv(
        "CONTROLLED_AGENT_ALLOW_SECURITY_SIMULATION",
        "true",
    )

    settings = get_settings()

    assert (
        settings.allow_security_simulation
        is True
    )


def test_security_simulation_is_forced_off_in_production(
    monkeypatch,
):
    monkeypatch.setenv(
        "CONTROLLED_AGENT_ENV",
        "production",
    )

    monkeypatch.setenv(
        "CONTROLLED_AGENT_ALLOW_SECURITY_SIMULATION",
        "true",
    )

    settings = get_settings()

    assert (
        settings.allow_security_simulation
        is False
    )


def test_api_rejects_security_simulation_when_disabled():
    agent = FakeAgent()

    request = CreateAgentRunRequest(
        message="Check order 45821.",
        simulate_lookup_injection=True,
    )

    settings = ApiSettings(
        environment="production",
        allow_security_simulation=False,
    )

    with pytest.raises(
        HTTPException,
    ) as exc_info:
        create_agent_run(
            request=request,
            agent=agent,
            settings=settings,
        )

    assert (
        exc_info.value.status_code
        == 403
    )

    assert agent.run_called is False

    assert (
        agent.simulate_lookup_injection
        is False
    )


def test_api_allows_explicit_development_security_simulation():
    agent = FakeAgent()

    request = CreateAgentRunRequest(
        message="Check order 45821.",
        simulate_lookup_injection=True,
    )

    settings = ApiSettings(
        environment="development",
        allow_security_simulation=True,
    )

    response = create_agent_run(
        request=request,
        agent=agent,
        settings=settings,
    )

    assert agent.run_called is True

    assert (
        agent.simulate_lookup_injection
        is True
    )

    assert (
        response.run_id
        == "run-test"
    )