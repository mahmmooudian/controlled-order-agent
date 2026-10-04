from __future__ import annotations

from controlled_agent.adapters.mock import MockOrderService
from controlled_agent.domain.schemas import (
    LookupOrderInput,
    LookupOrderOutput,
)
from controlled_agent.security.validation import (
    safe_validate_lookup_output,
    validate_lookup_input,
)
from controlled_agent.services.order import (
    OrderService,
    OrderServiceTimeoutError,
)


class LookupOrderToolError(Exception):
    """Base error for lookup_order."""


class LookupOrderTimeoutError(LookupOrderToolError):
    """Raised when lookup_order times out."""


def lookup_order(
    order_id: str,
    *,
    simulate_timeout: bool = False,
    simulate_injection: bool = False,
    service: OrderService | None = None,
) -> LookupOrderOutput:
    """
    READ-only order lookup tool.

    Flow:
    1. Validate tool input.
    2. Execute an OrderService.
    3. Treat returned data as untrusted.
    4. Allowlist and validate output.
    5. Return validated structured data.
    """

    validated_input: LookupOrderInput = (
        validate_lookup_input(order_id)
    )

    selected_service = service

    if selected_service is None:
        selected_service = MockOrderService(
            simulate_timeout=simulate_timeout,
            simulate_injection=simulate_injection,
        )

    try:
        raw_output = selected_service.get_order(
            validated_input.order_id
        )

    except OrderServiceTimeoutError as exc:
        raise LookupOrderTimeoutError(
            str(exc)
        ) from exc

    validation_result = (
        safe_validate_lookup_output(
            raw_output
        )
    )

    if not validation_result["success"]:
        raise LookupOrderToolError(
            "Invalid output returned by lookup_order: "
            + str(validation_result["error"])
        )

    discarded_fields = (
        validation_result["discarded_fields"]
    )

    if discarded_fields:
        print(
            "[SECURITY] Discarded untrusted fields:",
            discarded_fields,
        )

    return validation_result["data"]


MAX_RETRIES = 1


def lookup_order_with_retry(
    order_id: str,
    *,
    simulate_timeout: bool = False,
    simulate_injection: bool = False,
    service: OrderService | None = None,
) -> LookupOrderOutput:
    """
    Execute lookup_order with limited retry.

    Retry policy:
    - First attempt
    - Maximum one retry after timeout
    - No infinite retries
    """

    attempts = 0

    while True:
        try:
            attempts += 1

            print(
                f"[TOOL] lookup_order attempt {attempts}"
            )

            if service is None:
                return lookup_order(
                    order_id,
                    simulate_timeout=(
                        simulate_timeout
                        and attempts == 1
                    ),
                    simulate_injection=(
                        simulate_injection
                    ),
                )

            return lookup_order(
                order_id,
                service=service,
            )

        except LookupOrderTimeoutError as exc:
            print(
                f"[TIMEOUT] {exc}"
            )

            if attempts > MAX_RETRIES:
                print(
                    "[RETRY] Retry limit reached."
                )
                raise

            print(
                "[RETRY] Retrying once..."
            )