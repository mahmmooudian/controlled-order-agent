from __future__ import annotations

from typing import Any

import httpx

from controlled_agent.api.schemas import AgentRunResponse


class ApiClientError(RuntimeError):
    """
    Raised when the Controlled Agent API cannot
    be reached or returns an unsuccessful response.
    """


class ControlledAgentApiClient:
    """
    HTTP client used by desktop/UI applications
    to communicate with the FastAPI backend.

    The GUI must not call ControlledOrderAgent
    directly once migration is complete.
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
        try:
            payload = response.json()

        except ValueError:
            return response.text or "Unknown API error."

        if isinstance(payload, dict):
            detail = payload.get("detail")

            if detail is not None:
                return str(detail)

        return str(payload)

    # ========================================================
    # HEALTH
    # ========================================================

    def health(
        self,
    ) -> dict[str, Any]:
        response = self._request(
            "GET",
            "/health",
        )

        return response.json()

    def ready(
        self,
    ) -> bool:
        response = self._request(
            "GET",
            "/ready",
        )

        payload = response.json()

        return bool(
            payload.get("ready")
        )

    # ========================================================
    # CREATE RUN
    # ========================================================

    def create_run(
        self,
        message: str,
    ) -> AgentRunResponse:
        response = self._request(
            "POST",
            "/agent/runs",
            json={
                "message": message,
            },
        )

        return AgentRunResponse.model_validate(
            response.json()
        )

    # ========================================================
    # GET RUN
    # ========================================================

    def get_run(
        self,
        run_id: str,
    ) -> AgentRunResponse:
        response = self._request(
            "GET",
            f"/agent/runs/{run_id}",
        )

        return AgentRunResponse.model_validate(
            response.json()
        )

    # ========================================================
    # CONTINUE WITH INPUT
    # ========================================================

    def send_input(
        self,
        run_id: str,
        message: str,
    ) -> AgentRunResponse:
        response = self._request(
            "POST",
            f"/agent/runs/{run_id}/input",
            json={
                "message": message,
            },
        )

        return AgentRunResponse.model_validate(
            response.json()
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
        response = self._request(
            "POST",
            f"/agent/runs/{run_id}/approval",
            json={
                "approved": approved,
            },
        )

        return AgentRunResponse.model_validate(
            response.json()
        )

    # ========================================================
    # RESOURCE MANAGEMENT
    # ========================================================

    def close(
        self,
    ) -> None:
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