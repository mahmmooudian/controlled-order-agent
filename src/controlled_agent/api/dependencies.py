from __future__ import annotations

import os
from pathlib import Path

from controlled_agent.adapters.sqlite import (
    PersistentAuditLogger,
    PersistentTicketService,
)
from controlled_agent.persistence import (
    AgentRunRepository,
    ApprovalRepository,
    AuditRepository,
    Database,
    TicketRepository,
)
from controlled_agent.planners import RuleBasedPlanner
from controlled_agent.runtime import ControlledOrderAgent


DEFAULT_DATABASE_PATH = Path(
    "data/controlled_agent.db"
)


def get_database_path() -> Path:
    """
    Resolve the SQLite database path.

    It can be overridden through:
        CONTROLLED_AGENT_DB
    """

    raw_path = os.getenv(
        "CONTROLLED_AGENT_DB"
    )

    if raw_path:
        return Path(raw_path)

    return DEFAULT_DATABASE_PATH


def build_agent(
    database_path: Path | str | None = None,
) -> ControlledOrderAgent:
    """
    Build one fully wired production Agent runtime.
    """

    db_path = (
        Path(database_path)
        if database_path is not None
        else get_database_path()
    )

    db_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    database = Database(
        db_path
    )

    database.initialize()

    run_repository = AgentRunRepository(
        database
    )

    approval_repository = ApprovalRepository(
        database
    )

    audit_repository = AuditRepository(
        database
    )

    ticket_repository = TicketRepository(
        database
    )

    audit_logger = PersistentAuditLogger(
        audit_repository
    )

    ticket_service = PersistentTicketService(
        ticket_repository
    )

    return ControlledOrderAgent(
        RuleBasedPlanner(),
        audit_logger=audit_logger,
        ticket_service=ticket_service,
        run_repository=run_repository,
        approval_repository=approval_repository,
    )


def get_agent() -> ControlledOrderAgent:
    """
    FastAPI dependency provider.
    """

    return build_agent()