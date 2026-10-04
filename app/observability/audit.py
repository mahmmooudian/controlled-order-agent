from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# AUDIT EVENT MODEL
# ============================================================

class AuditEvent(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    timestamp: str

    step: int = Field(
        ge=0,
    )

    event: str

    detail: str


# ============================================================
# AUDIT LOGGER
# ============================================================

class AuditLogger:
    """
    Lightweight in-memory audit logger.

    It stores operational events only.
    It does NOT store hidden chain-of-thought.
    """

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def log(
        self,
        *,
        step: int,
        event: str,
        detail: str,
    ) -> None:

        timestamp = (
            datetime.now(
                timezone.utc
            )
            .isoformat()
        )

        audit_event = AuditEvent(
            timestamp=timestamp,
            step=step,
            event=event,
            detail=detail,
        )

        self.events.append(
            audit_event
        )

    def get_events(
        self,
    ) -> list[AuditEvent]:
        return list(
            self.events
        )

    def clear(
        self,
    ) -> None:
        self.events.clear()

    def print_summary(
        self,
    ) -> None:
        """
        Print a readable execution summary.
        """

        print(
            "\n--- EXECUTION / AUDIT SUMMARY ---"
        )

        if not self.events:
            print(
                "No audit events recorded."
            )
            return

        for item in self.events:
            print(
                f"[step {item.step}] "
                f"{item.event}: "
                f"{item.detail}"
            )