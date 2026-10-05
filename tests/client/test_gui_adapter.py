from controlled_agent.api.schemas import (
    AgentRunResponse,
    AuditEventResponse,
)
from controlled_agent.client.gui_adapter import (
    GuiAgentAdapter,
)


class FakeApiClient:
    def __init__(self):
        self.last_message = None
        self.last_injection_flag = None
        self.last_input = None
        self.last_approval = None
        self.closed = False

    def create_run(
        self,
        message: str,
        *,
        simulate_lookup_injection: bool = False,
    ) -> AgentRunResponse:
        self.last_message = message

        self.last_injection_flag = (
            simulate_lookup_injection
        )

        return AgentRunResponse(
            run_id="run-1",
            status="waiting_for_approval",
            steps=2,
            finished=False,
            awaiting_user_input=False,
            awaiting_approval=True,
            human_approved=None,
            order_id="8452",
            order_status="delayed",
            days_delayed=5,
            ticket_id=None,
            final_message=(
                "Human approval is required."
            ),
        )

    def send_input(
        self,
        run_id: str,
        message: str,
    ) -> AgentRunResponse:
        self.last_input = (
            run_id,
            message,
        )

        return AgentRunResponse(
            run_id=run_id,
            status="waiting_for_approval",
            steps=2,
            finished=False,
            awaiting_user_input=False,
            awaiting_approval=True,
            human_approved=None,
            order_id="8452",
            order_status="delayed",
            days_delayed=5,
            ticket_id=None,
            final_message=(
                "Human approval is required."
            ),
        )

    def submit_approval(
        self,
        run_id: str,
        *,
        approved: bool,
    ) -> AgentRunResponse:
        self.last_approval = (
            run_id,
            approved,
        )

        return AgentRunResponse(
            run_id=run_id,
            status="done",
            steps=4,
            finished=True,
            awaiting_user_input=False,
            awaiting_approval=False,
            human_approved=approved,
            order_id="8452",
            order_status="delayed",
            days_delayed=5,
            ticket_id=(
                "TCK-1001"
                if approved
                else None
            ),
            final_message="Finished.",
        )

    def get_audit(
        self,
        run_id: str,
    ) -> list[AuditEventResponse]:
        return [
            AuditEventResponse(
                timestamp=(
                    "2026-10-05T00:00:00+00:00"
                ),
                step=1,
                event="lookup_order_called",
                detail="order_id=8452",
            )
        ]

    def close(self):
        self.closed = True


def test_gui_adapter_maps_api_state():
    client = FakeApiClient()

    adapter = GuiAgentAdapter(
        client=client,
    )

    state = adapter.run(
        "Check order 8452."
    )

    assert state.run_id == "run-1"

    assert (
        state.status.value
        == "waiting_for_approval"
    )

    assert state.order_id == "8452"

    assert (
        state.order_status.value
        == "delayed"
    )

    assert state.days_delayed == 5

    assert state.awaiting_approval is True

    assert state.human_approved is None


def test_gui_adapter_refreshes_audit():
    client = FakeApiClient()

    adapter = GuiAgentAdapter(
        client=client,
    )

    adapter.run(
        "Check order 8452."
    )

    events = (
        adapter.audit.get_events()
    )

    assert len(events) == 1

    assert (
        events[0].event
        == "lookup_order_called"
    )

    assert events[0].step == 1


def test_gui_adapter_resumes_approval():
    client = FakeApiClient()

    adapter = GuiAgentAdapter(
        client=client,
    )

    state = adapter.run(
        "Check order 8452."
    )

    result = (
        adapter.resume_with_approval(
            state,
            True,
        )
    )

    assert result.finished is True

    assert (
        result.human_approved
        is True
    )

    assert (
        result.ticket_id
        == "TCK-1001"
    )

    assert client.last_approval == (
        "run-1",
        True,
    )


def test_gui_adapter_forwards_injection_flag():
    client = FakeApiClient()

    adapter = GuiAgentAdapter(
        client=client,
        simulate_lookup_injection=True,
    )

    adapter.run(
        "Check order 45821."
    )

    assert (
        client.last_injection_flag
        is True
    )