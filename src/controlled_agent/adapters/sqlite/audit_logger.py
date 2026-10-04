from __future__ import annotations

from controlled_agent.observability import AuditLogger
from controlled_agent.persistence import AuditRepository


class PersistentAuditLogger(AuditLogger):
    """
    Audit logger that preserves the existing in-memory API
    while also persisting every event to SQLite.

    Important:
    clear() only clears the in-memory buffer.
    Historical database records are never deleted implicitly.
    """

    def __init__(
        self,
        repository: AuditRepository,
        *,
        run_id: str,
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
        Record the event in memory and persist it.
        """

        super().log(
            step=step,
            event=event,
            detail=detail,
        )

        audit_event = self.events[-1]

        self.repository.add(
            audit_event,
            run_id=self.run_id,
        )

    def set_run_id(
        self,
        run_id: str,
    ) -> None:
        """
        Bind future events to another Agent run.
        """

        self.run_id = run_id

    def clear_persisted(
        self,
    ) -> None:
        """
        Explicitly remove persisted events for
        the currently bound run.

        This is intentionally separate from clear().
        """

        self.repository.clear_for_run(
            self.run_id
        )