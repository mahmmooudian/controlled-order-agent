import re
from typing import Any

from pydantic import ValidationError

from controlled_agent.domain.schemas import (
    LookupOrderInput,
    LookupOrderOutput,
)


ORDER_ID_PATTERN = re.compile(r"^\d{4,12}$")


# ============================================================
# ORDER ID VALIDATION
# ============================================================

def validate_order_id(order_id: str) -> bool:
    """
    Lightweight validation before calling lookup_order.
    """

    if not isinstance(order_id, str):
        return False

    order_id = order_id.strip()

    return bool(
        ORDER_ID_PATTERN.fullmatch(order_id)
    )


# ============================================================
# LOOKUP INPUT VALIDATION
# ============================================================

def validate_lookup_input(
    order_id: str,
) -> LookupOrderInput:
    """
    Validate lookup_order input using the Pydantic schema.
    """

    return LookupOrderInput(
        order_id=order_id,
    )


# ============================================================
# TOOL OUTPUT SANITIZATION
# ============================================================

def sanitize_lookup_output(
    raw_output: dict[str, Any],
) -> tuple[LookupOrderOutput, list[str]]:
    """
    Treat tool output as untrusted data.

    Only allowed fields are passed to the validated model.
    Unknown fields are discarded.
    """

    if not isinstance(raw_output, dict):
        raise ValueError(
            "Tool output must be a dictionary."
        )

    allowed_fields = {
        "order_id",
        "status",
        "days_delayed",
    }

    received_fields = set(
        raw_output.keys()
    )

    discarded_fields = sorted(
        received_fields - allowed_fields
    )

    safe_payload = {
        key: raw_output[key]
        for key in allowed_fields
        if key in raw_output
    }

    validated_output = (
        LookupOrderOutput.model_validate(
            safe_payload
        )
    )

    return (
        validated_output,
        discarded_fields,
    )


# ============================================================
# SAFE VALIDATION WRAPPER
# ============================================================

def safe_validate_lookup_output(
    raw_output: dict[str, Any],
) -> dict:
    """
    Safe wrapper for Agent runtime.
    """

    try:
        parsed, discarded = (
            sanitize_lookup_output(
                raw_output
            )
        )

        return {
            "success": True,
            "data": parsed,
            "discarded_fields": discarded,
            "error": None,
        }

    except (
        ValidationError,
        ValueError,
        TypeError,
    ) as exc:

        return {
            "success": False,
            "data": None,
            "discarded_fields": [],
            "error": str(exc),
        }