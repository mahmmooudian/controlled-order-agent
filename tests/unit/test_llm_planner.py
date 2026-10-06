from __future__ import annotations

from types import SimpleNamespace

import pytest


pytest.importorskip("openai")


import controlled_agent.planners.llm as llm_module

from controlled_agent.domain.schemas import AgentDecision
from controlled_agent.domain.state import AgentState
from controlled_agent.planners.llm import LLMPlanner


# ============================================================
# INITIALIZATION / CONFIGURATION
# ============================================================

def test_llm_planner_requires_api_key(
    monkeypatch,
) -> None:
    monkeypatch.delenv(
        "OPENAI_API_KEY",
        raising=False,
    )

    monkeypatch.setenv(
        "OPENAI_MODEL",
        "test-model",
    )

    with pytest.raises(
        RuntimeError,
        match="OPENAI_API_KEY is missing",
    ):
        LLMPlanner()


def test_llm_planner_requires_model(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "OPENAI_API_KEY",
        "test-api-key",
    )

    monkeypatch.delenv(
        "OPENAI_MODEL",
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match="OPENAI_MODEL is missing",
    ):
        LLMPlanner()


def test_llm_planner_initializes_openai_client(
    monkeypatch,
) -> None:
    captured: dict[str, str] = {}

    class FakeOpenAI:
        def __init__(
            self,
            *,
            api_key: str,
        ) -> None:
            captured["api_key"] = api_key

    monkeypatch.setattr(
        llm_module,
        "OpenAI",
        FakeOpenAI,
    )

    monkeypatch.setenv(
        "OPENAI_API_KEY",
        "test-api-key",
    )

    monkeypatch.setenv(
        "OPENAI_MODEL",
        "test-model",
    )

    planner = LLMPlanner()

    assert captured["api_key"] == "test-api-key"
    assert planner.model == "test-model"
    assert isinstance(
        planner.client,
        FakeOpenAI,
    )


# ============================================================
# SAFE MODEL CONTEXT
# ============================================================

def test_safe_state_contains_only_expected_fields() -> None:
    state = AgentState(
        user_message="Check order 8452.",
    )

    safe_state = LLMPlanner._safe_state(
        state
    )

    assert set(
        safe_state.keys()
    ) == {
        "user_message",
        "order_id",
        "order_status",
        "days_delayed",
        "awaiting_approval",
        "human_approved",
        "ticket_id",
        "steps",
        "status",
    }

    assert (
        safe_state["user_message"]
        == "Check order 8452."
    )

    assert "latest_user_message" not in safe_state


# ============================================================
# STRUCTURED DECISION
# ============================================================

def test_decide_uses_structured_response_schema() -> None:
    captured: dict = {}

    parsed_decision = object()

    class FakeResponses:
        def parse(
            self,
            **kwargs,
        ):
            captured.update(
                kwargs
            )

            return SimpleNamespace(
                output_parsed=parsed_decision
            )

    class FakeClient:
        def __init__(self) -> None:
            self.responses = FakeResponses()

    planner = object.__new__(
        LLMPlanner
    )

    planner.client = FakeClient()
    planner.model = "test-model"

    state = AgentState(
        user_message="Check order 8452.",
    )

    result = planner.decide(
        state
    )

    assert result is parsed_decision

    assert (
        captured["model"]
        == "test-model"
    )

    assert (
        captured["text_format"]
        is AgentDecision
    )

    assert (
        captured["input"][0]["role"]
        == "system"
    )

    assert (
        captured["input"][1]["role"]
        == "user"
    )

    payload = str(
        captured["input"]
    )

    assert "test-api-key" not in payload
    assert "OPENAI_API_KEY" not in payload


def test_decide_rejects_missing_structured_output() -> None:
    class FakeResponses:
        def parse(
            self,
            **kwargs,
        ):
            return SimpleNamespace(
                output_parsed=None
            )

    class FakeClient:
        def __init__(self) -> None:
            self.responses = FakeResponses()

    planner = object.__new__(
        LLMPlanner
    )

    planner.client = FakeClient()
    planner.model = "test-model"

    state = AgentState(
        user_message="Check order 8452.",
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "LLM returned no structured decision"
        ),
    ):
        planner.decide(
            state
        )