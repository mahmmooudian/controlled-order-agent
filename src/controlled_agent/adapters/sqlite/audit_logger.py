from __future__ import annotations

from controlled_agent.observability import AuditLogger
from controlled_agent.persistence import AuditRepository


class PersistentAuditLogger(AuditLogger):
    """
    Audit logger that keeps the normal in-memory
    AuditLogger API while optionally persisting
    events to SQLite.

    The logger may be created before an Agent run
    exists. Once a run_id is assigned by the Runtime,
    subsequent events are persisted under that run.
    """

    def __init__(
        self,
        repository: AuditRepository,
        *,
        run_id: str | None = None,
    ) -> None:
        super().__init__()

        self.repository = repository
        self.run_id = run_id

    def log(
        self,
        *,
        step: int,
        event: str,
        detail: str,
    ) -> None:
        """
        Always keep the event in memory.

        Persist it only when the logger is currently
        bound to a valid Agent run.
        """

        super().log(
            step=step,
            event=event,
            detail=detail,
        )

        if self.run_id is None:
            return

        audit_event = self.events[-1]

        self.repository.add(
            audit_event,
            run_id=self.run_id,
        )

    def set_run_id(
        self,
        run_id: str | None,
    ) -> None:
        """
        Bind or unbind future audit events
        from an Agent run.
        """

        self.run_id = run_id

    def clear_persisted(
        self,
    ) -> None:
        """
        Explicitly remove persisted events for
        the currently bound run.

        Normal clear() still clears only memory.
        """

        if self.run_id is None:
            raise RuntimeError(
                "PersistentAuditLogger is not "
                "bound to an Agent run."
            )

        self.repository.clear_for_run(
            self.run_id
        )