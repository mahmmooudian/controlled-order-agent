import httpx
import pytest
import json
from controlled_agent.client import (
    ApiClientError,
    ControlledAgentApiClient,
)


RUN_RESPONSE = {
    "run_id": "run-123",
    "status": "done",
    "steps": 2,
    "finished": True,
    "awaiting_user_input": False,
    "awaiting_approval": False,
    "order_id": "45821",
    "order_status": "shipped",
    "days_delayed": 2,
    "ticket_id": None,
    "final_message": "Order is shipped.",
}


def create_transport():
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:

        if request.url.path == "/health":
            return httpx.Response(
                200,
                json={
                    "status": "ok",
                    "service": "controlled-order-agent",
                    "version": "2.0.0.dev0",
                },
            )

        if request.url.path == "/ready":
            return httpx.Response(
                200,
                json={
                    "ready": True,
                    "service": "controlled-order-agent",
                },
            )

        if (
            request.method == "POST"
            and request.url.path == "/agent/runs"
        ):
            return httpx.Response(
                201,
                json=RUN_RESPONSE,
            )

        if (
            request.method == "GET"
            and request.url.path
            == "/agent/runs/run-123"
        ):
            return httpx.Response(
                200,
                json=RUN_RESPONSE,
            )

        if (
            request.method == "POST"
            and request.url.path
            == "/agent/runs/run-123/input"
        ):
            return httpx.Response(
                200,
                json=RUN_RESPONSE,
            )

        if (
            request.method == "POST"
            and request.url.path
            == "/agent/runs/run-123/approval"
        ):
            return httpx.Response(
                200,
                json=RUN_RESPONSE,
            )

        if (
            request.method == "GET"
            and request.url.path
            == "/agent/runs/run-123/audit"
        ):
            return httpx.Response(
                200,
                json=[
                    {
                        "timestamp": (
                            "2026-10-05T00:00:00+00:00"
                        ),
                        "step": 1,
                        "event": "request_received",
                        "detail": "Request accepted.",
                    }
                ],
            )

        return httpx.Response(
            404,
            json={
                "detail": "Not found.",
            },
        )

    return httpx.MockTransport(
        handler
    )


def test_api_client_health_and_ready():
    client = ControlledAgentApiClient(
        transport=create_transport()
    )

    health = client.health()

    assert health["status"] == "ok"
    assert client.ready() is True

    client.close()


def test_api_client_create_and_get_run():
    client = ControlledAgentApiClient(
        transport=create_transport()
    )

    created = client.create_run(
        "Check order 45821."
    )

    assert created.run_id == "run-123"
    assert created.order_id == "45821"
    assert created.finished is True

    restored = client.get_run(
        created.run_id
    )

    assert restored.run_id == created.run_id

    client.close()


def test_api_client_continue_and_approve():
    client = ControlledAgentApiClient(
        transport=create_transport()
    )

    continued = client.send_input(
        "run-123",
        "8452",
    )

    assert continued.run_id == "run-123"

    approved = client.submit_approval(
        "run-123",
        approved=True,
    )

    assert approved.run_id == "run-123"

    client.close()


def test_api_client_get_audit():
    client = ControlledAgentApiClient(
        transport=create_transport()
    )

    events = client.get_audit(
        "run-123"
    )

    assert len(events) == 1

    assert (
        events[0].event
        == "request_received"
    )

    assert events[0].step == 1

    client.close()


def test_api_client_reports_http_errors():
    client = ControlledAgentApiClient(
        transport=create_transport()
    )

    with pytest.raises(
        ApiClientError,
        match="404",
    ):
        client.get_run(
            "missing-run"
        )

    client.close()


def test_api_client_reports_connection_errors():
    def broken_handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ConnectError(
            "Connection refused.",
            request=request,
        )

    client = ControlledAgentApiClient(
        transport=httpx.MockTransport(
            broken_handler
        )
    )

    with pytest.raises(
        ApiClientError,
        match="Could not connect",
    ):
        client.health()

    client.close()
def test_api_client_sends_injection_flag():
    observed = {
        "simulate_lookup_injection": None,
    }

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        payload = json.loads(
            request.content.decode(
                "utf-8"
            )
        )

        observed[
            "simulate_lookup_injection"
        ] = payload[
            "simulate_lookup_injection"
        ]

        return httpx.Response(
            201,
            json=RUN_RESPONSE,
        )

    client = ControlledAgentApiClient(
        transport=httpx.MockTransport(
            handler
        )
    )

    client.create_run(
        "Check order 45821.",
        simulate_lookup_injection=True,
    )

    assert (
        observed[
            "simulate_lookup_injection"
        ]
        is True
    )

    client.close()