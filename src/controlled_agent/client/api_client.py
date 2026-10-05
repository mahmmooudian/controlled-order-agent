from __future__ import annotations

import time

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

    Reliability policy:

    - GET requests may be retried because they are
      read-only and idempotent.
    - POST requests are never retried automatically.
    - Only transient network errors and selected
      gateway/service errors are retryable.
    - Connect/read/write/pool timeouts are configured
      independently.
    """

    RETRYABLE_STATUS_CODES = {
        502,
        503,
        504,
    }

    RETRYABLE_EXCEPTIONS = (
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.PoolTimeout,
    )

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        *,
        timeout: float | httpx.Timeout | None = None,
        connect_timeout: float = 3.0,
        read_timeout: float = 10.0,
        write_timeout: float = 10.0,
        pool_timeout: float = 3.0,
        max_get_retries: int = 2,
        retry_backoff: float = 0.10,
        transport: httpx.BaseTransport | None = None,
    ) -> None:

        if max_get_retries < 0:
            raise ValueError(
                "max_get_retries must be >= 0."
            )

        if retry_backoff < 0:
            raise ValueError(
                "retry_backoff must be >= 0."
            )

        self.base_url = base_url.rstrip("/")

        self.max_get_retries = (
            max_get_retries
        )

        self.retry_backoff = (
            retry_backoff
        )

        if timeout is None:
            resolved_timeout = httpx.Timeout(
                connect=connect_timeout,
                read=read_timeout,
                write=write_timeout,
                pool=pool_timeout,
            )
        elif isinstance(
            timeout,
            httpx.Timeout,
        ):
            resolved_timeout = timeout
        else:
            # Backwards compatibility for callers
            # that already pass timeout=3.0, etc.
            resolved_timeout = httpx.Timeout(
                timeout
            )

        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=resolved_timeout,
            transport=transport,
        )

    # ========================================================
    # RETRY POLICY
    # ========================================================

    @staticmethod
    def _is_retryable_method(
        method: str,
    ) -> bool:
        """
        Only retry read-only HTTP operations.

        POST requests may produce side effects, so
        they must never be replayed automatically.
        """

        return (
            method.upper()
            == "GET"
        )

    def _can_retry(
        self,
        method: str,
        attempt: int,
    ) -> bool:
        """
        Return whether another attempt is allowed.

        attempt is zero-based.
        """

        return (
            self._is_retryable_method(
                method
            )
            and attempt
            < self.max_get_retries
        )

    def _sleep_before_retry(
        self,
        attempt: int,
    ) -> None:
        """
        Apply a small bounded linear backoff.

        Examples with retry_backoff=0.1:
            retry 1 -> 0.1 seconds
            retry 2 -> 0.2 seconds
        """

        delay = (
            self.retry_backoff
            * (attempt + 1)
        )

        if delay > 0:
            time.sleep(
                delay
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
        Execute one HTTP request.

        GET requests receive bounded retry handling
        for transient failures.

        POST requests are executed exactly once to
        avoid accidental duplicate side effects.
        """

        normalized_method = (
            method.upper()
        )

        attempt = 0

        while True:

            try:
                response = self._client.request(
                    normalized_method,
                    path,
                    json=json,
                )

            except self.RETRYABLE_EXCEPTIONS as exc:

                if self._can_retry(
                    normalized_method,
                    attempt,
                ):
                    self._sleep_before_retry(
                        attempt
                    )

                    attempt += 1
                    continue

                if isinstance(
                    exc,
                    httpx.TimeoutException,
                ):
                    raise ApiClientError(
                        (
                            "Controlled Order Agent API "
                            "request timed out."
                        )
                    ) from exc

                raise ApiClientError(
                    (
                        "Could not connect to "
                        "Controlled Order Agent API."
                    )
                ) from exc

            except httpx.TimeoutException as exc:
                # Other timeout subclasses that are
                # intentionally not retried.
                raise ApiClientError(
                    (
                        "Controlled Order Agent API "
                        "request timed out."
                    )
                ) from exc

            except httpx.RequestError as exc:
                # Non-transient request errors are not
                # automatically replayed.
                raise ApiClientError(
                    (
                        "Could not connect to "
                        "Controlled Order Agent API."
                    )
                ) from exc

            if response.is_success:
                return response

            if (
                response.status_code
                in self.RETRYABLE_STATUS_CODES
                and self._can_retry(
                    normalized_method,
                    attempt,
                )
            ):
                self._sleep_before_retry(
                    attempt
                )

                attempt += 1
                continue

            detail = self._extract_error_detail(
                response
            )

            raise ApiClientError(
                (
                    f"API request failed "
                    f"({response.status_code}): "
                    f"{detail}"
                )
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

        POST is intentionally not retried because
        creating a run may have side effects.

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

        This POST is never automatically retried.
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

        Approval is security-sensitive and must
        never be automatically replayed.
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