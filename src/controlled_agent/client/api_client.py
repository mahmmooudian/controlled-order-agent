from __future__ import annotations

from typing import Any

import httpx

from controlled_agent.api.schemas import (
    AgentRunResponse,
    AuditEventResponse,
)


# ============================================================
# CLIENT ERRORS
# ============================================================

class ApiClientError(RuntimeError):
    """
    Raised when the Controlled Agent API cannot
    be reached or returns an unsuccessful response.
    """


# ============================================================
# CONTROLLED AGENT API CLIENT
# ============================================================

class ControlledAgentApiClient:
    """
    HTTP client used by desktop/UI applications
    to communicate with the FastAPI backend.

    The GUI must use this client instead of calling
    ControlledOrderAgent directly.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        *,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:

        self.base_url = base_url.rstrip("/")

        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            transport=transport,
        )

    # ========================================================
    # INTERNAL REQUEST HANDLING
    # ========================================================

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """
        Execute one HTTP request and convert
        connection/API failures into ApiClientError.
        """

        try:
            response = self._client.request(
                method,
                path,
                json=json,
            )

        except httpx.RequestError as exc:
            raise ApiClientError(
                "Could not connect to "
                "Controlled Order Agent API."
            ) from exc

        if response.is_success:
            return response

        detail = self._extract_error_detail(
            response
        )

        raise ApiClientError(
            f"API request failed "
            f"({response.status_code}): "
            f"{detail}"
        )

    @staticmethod
    def _extract_error_detail(
        response: httpx.Response,
    ) -> str:
        """
        Extract a readable error message from
        FastAPI-style JSON error responses.
        """

        try:
            payload = response.json()

        except ValueError:
            return (
                response.text
                or "Unknown API error."
            )

        if isinstance(
            payload,
            dict,
        ):
            detail = payload.get(
                "detail"
            )

            if detail is not None:
                return str(
                    detail
                )

        return str(
            payload
        )

    # ========================================================
    # HEALTH / READINESS
    # ========================================================

    def health(
        self,
    ) -> dict[str, Any]:
        """
        Return API liveness information.
        """

        response = self._request(
            "GET",
            "/health",
        )

        return response.json()

    def ready(
        self,
    ) -> bool:
        """
        Return whether the API reports itself
        as ready for requests.
        """

        response = self._request(
            "GET",
            "/ready",
        )

        payload = response.json()

        return bool(
            payload.get(
                "ready"
            )
        )

    # ========================================================
    # CREATE RUN
    # ========================================================

    def create_run(
        self,
        message: str,
        *,
        simulate_lookup_injection: bool = False,
    ) -> AgentRunResponse:
        """
        Create a new Agent execution.

        simulate_lookup_injection is used only
        by the controlled security demonstration.
        """

        response = self._request(
            "POST",
            "/agent/runs",
            json={
                "message": message,
                "simulate_lookup_injection": (
                    simulate_lookup_injection
                ),
            },
        )

        return (
            AgentRunResponse.model_validate(
                response.json()
            )
        )

    # ========================================================
    # GET RUN
    # ========================================================

    def get_run(
        self,
        run_id: str,
    ) -> AgentRunResponse:
        """
        Restore the latest persisted state
        of an Agent run.
        """

        response = self._request(
            "GET",
            f"/agent/runs/{run_id}",
        )

        return (
            AgentRunResponse.model_validate(
                response.json()
            )
        )

    # ========================================================
    # CONTINUE WITH USER INPUT
    # ========================================================

    def send_input(
        self,
        run_id: str,
        message: str,
    ) -> AgentRunResponse:
        """
        Continue a run that is waiting
        for additional user input.
        """

        response = self._request(
            "POST",
            f"/agent/runs/{run_id}/input",
            json={
                "message": message,
            },
        )

        return (
            AgentRunResponse.model_validate(
                response.json()
            )
        )

    # ========================================================
    # HUMAN APPROVAL
    # ========================================================

    def submit_approval(
        self,
        run_id: str,
        *,
        approved: bool,
    ) -> AgentRunResponse:
        """
        Submit the user's explicit decision for
        a sensitive WRITE action.
        """

        response = self._request(
            "POST",
            f"/agent/runs/{run_id}/approval",
            json={
                "approved": approved,
            },
        )

        return (
            AgentRunResponse.model_validate(
                response.json()
            )
        )

    # ========================================================
    # AUDIT / EXECUTION TRACE
    # ========================================================

    def get_audit(
        self,
        run_id: str,
    ) -> list[AuditEventResponse]:
        """
        Return the persisted operational trace
        for one Agent run.
        """

        response = self._request(
            "GET",
            f"/agent/runs/{run_id}/audit",
        )

        payload = response.json()

        return [
            AuditEventResponse.model_validate(
                item
            )
            for item in payload
        ]

    # ========================================================
    # RESOURCE MANAGEMENT
    # ========================================================

    def close(
        self,
    ) -> None:
        """
        Close the underlying HTTP connection pool.
        """

        self._client.close()

    def __enter__(
        self,
    ) -> "ControlledAgentApiClient":
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.close()