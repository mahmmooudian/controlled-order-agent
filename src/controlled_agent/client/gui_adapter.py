from __future__ import annotations

from dataclasses import dataclass

from controlled_agent.api.schemas import (
    AgentRunResponse,
    AuditEventResponse,
)
from controlled_agent.client.api_client import (
    ControlledAgentApiClient,
)


# ============================================================
# GUI-COMPATIBLE VALUE
# ============================================================

@dataclass(frozen=True)
class GuiValue:
    """
    Small compatibility wrapper.

    The existing Qt GUI expects enum-like objects
    exposing a `.value` attribute.
    """

    value: str


# ============================================================
# GUI-COMPATIBLE STATE
# ============================================================

@dataclass
class GuiAgentState:
    """
    Public API state adapted to the interface
    currently expected by gui_qt.py.
    """

    run_id: str

    status: GuiValue

    steps: int

    finished: bool

    awaiting_user_input: bool

    awaiting_approval: bool

    human_approved: bool | None

    order_id: str | None

    order_status: GuiValue | None

    days_delayed: int | None

    ticket_id: str | None

    final_message: str | None


# ============================================================
# AUDIT COMPATIBILITY PROXY
# ============================================================

class GuiAuditProxy:
    """
    Preserve the existing:

        self.agent.audit.get_events()

    GUI contract without exposing Runtime objects.
    """

    def __init__(
        self,
        adapter: "GuiAgentAdapter",
    ) -> None:
        self._adapter = adapter

    def get_events(
        self,
    ) -> list[AuditEventResponse]:
        return list(
            self._adapter._audit_events
        )


# ============================================================
# GUI AGENT ADAPTER
# ============================================================

class GuiAgentAdapter:
    """
    Compatibility layer between the existing
    PySide GUI and the HTTP API.

    The GUI sees an Agent-like interface, but
    no ControlledOrderAgent Runtime is executed
    inside the desktop process.
    """

    def __init__(
        self,
        *,
        client: ControlledAgentApiClient | None = None,
        simulate_lookup_injection: bool = False,
    ) -> None:

        self.client = (
            client
            if client is not None
            else ControlledAgentApiClient()
        )

        self.simulate_lookup_injection = (
            simulate_lookup_injection
        )

        self.current_run_id: str | None = None

        self._audit_events: list[
            AuditEventResponse
        ] = []

        self.audit = GuiAuditProxy(
            self
        )

    # ========================================================
    # STATE MAPPING
    # ========================================================

    @staticmethod
    def _to_gui_state(
        response: AgentRunResponse,
    ) -> GuiAgentState:

        order_status = None

        if response.order_status is not None:
            order_status = GuiValue(
                response.order_status
            )

        return GuiAgentState(
            run_id=response.run_id,
            status=GuiValue(
                response.status
            ),
            steps=response.steps,
            finished=response.finished,
            awaiting_user_input=(
                response.awaiting_user_input
            ),
            awaiting_approval=(
                response.awaiting_approval
            ),
            human_approved=(
                response.human_approved
            ),
            order_id=response.order_id,
            order_status=order_status,
            days_delayed=(
                response.days_delayed
            ),
            ticket_id=response.ticket_id,
            final_message=(
                response.final_message
            ),
        )

    # ========================================================
    # AUDIT SYNC
    # ========================================================

    def _refresh_audit(
        self,
    ) -> None:

        if self.current_run_id is None:
            self._audit_events = []
            return

        self._audit_events = (
            self.client.get_audit(
                self.current_run_id
            )
        )

    # ========================================================
    # NEW RUN
    # ========================================================

    def run(
        self,
        user_message: str,
    ) -> GuiAgentState:

        response = self.client.create_run(
            user_message,
            simulate_lookup_injection=(
                self.simulate_lookup_injection
            ),
        )

        self.current_run_id = (
            response.run_id
        )

        self._refresh_audit()

        return self._to_gui_state(
            response
        )

    # ========================================================
    # RESUME WITH USER INPUT
    # ========================================================

    def resume_with_user_input(
        self,
        state: GuiAgentState,
        user_message: str,
    ) -> GuiAgentState:

        response = self.client.send_input(
            state.run_id,
            user_message,
        )

        self.current_run_id = (
            response.run_id
        )

        self._refresh_audit()

        return self._to_gui_state(
            response
        )

    # ========================================================
    # HUMAN APPROVAL
    # ========================================================

    def resume_with_approval(
        self,
        state: GuiAgentState,
        approved: bool,
    ) -> GuiAgentState:

        response = (
            self.client.submit_approval(
                state.run_id,
                approved=approved,
            )
        )

        self.current_run_id = (
            response.run_id
        )

        self._refresh_audit()

        return self._to_gui_state(
            response
        )

    # ========================================================
    # RESOURCE MANAGEMENT
    # ========================================================

    def close(
        self,
    ) -> None:
        self.client.close()