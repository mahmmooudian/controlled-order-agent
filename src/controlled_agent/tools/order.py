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

    Security flow:
    1. Validate tool input.
    2. Execute an OrderService.
    3. Treat returned data as untrusted.
    4. Allowlist and validate output fields.
    5. Verify returned order_id matches requested order_id.
    6. Report discarded untrusted fields.
    7. Return validated structured output.
    """

    # --------------------------------------------------------
    # STEP 1: Validate input
    # --------------------------------------------------------

    validated_input: LookupOrderInput = (
        validate_lookup_input(order_id)
    )

    # --------------------------------------------------------
    # STEP 2: Select service
    # --------------------------------------------------------

    selected_service = service

    if selected_service is None:
        selected_service = MockOrderService(
            simulate_timeout=simulate_timeout,
            simulate_injection=simulate_injection,
        )

    # --------------------------------------------------------
    # STEP 3: Call service
    # --------------------------------------------------------

    try:
        raw_output = selected_service.get_order(
            validated_input.order_id
        )

    except OrderServiceTimeoutError as exc:
        raise LookupOrderTimeoutError(
            str(exc)
        ) from exc

    # --------------------------------------------------------
    # STEP 4: Validate untrusted output
    # --------------------------------------------------------

    validation_result = safe_validate_lookup_output(
        raw_output
    )

    if not validation_result["success"]:
        raise LookupOrderToolError(
            "Invalid output returned by lookup_order: "
            + str(validation_result["error"])
        )

    validated_output: LookupOrderOutput = (
        validation_result["data"]
    )

    # --------------------------------------------------------
    # STEP 5: Integrity check
    # --------------------------------------------------------

    if (
        validated_output.order_id
        != validated_input.order_id
    ):
        raise LookupOrderToolError(
            "Order integrity check failed: "
            f"requested order_id={validated_input.order_id}, "
            f"returned order_id={validated_output.order_id}"
        )

    # --------------------------------------------------------
    # STEP 6: Security visibility
    # --------------------------------------------------------

    discarded_fields = (
        validation_result["discarded_fields"]
    )

    if discarded_fields:
        print(
            "[SECURITY] Discarded untrusted fields:",
            discarded_fields,
        )

    # --------------------------------------------------------
    # STEP 7: Return safe structured result
    # --------------------------------------------------------

    return validated_output


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

            # Preserve the original demo behaviour:
            # the built-in mock only times out on the first attempt.
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