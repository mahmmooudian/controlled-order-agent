from __future__ import annotations

import os
import sqlite3

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
from controlled_agent.planners import (
    RuleBasedPlanner,
)
from controlled_agent.runtime import (
    ControlledOrderAgent,
)


DEFAULT_DATABASE_PATH = Path(
    "data/controlled_agent.db"
)


# ============================================================
# DATABASE PATH
# ============================================================

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
        return Path(
            raw_path
        )

    return DEFAULT_DATABASE_PATH


# ============================================================
# DATABASE
# ============================================================

def build_database(
    database_path: Path | str | None = None,
) -> Database:
    """
    Create and initialize one SQLite database
    provider.
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

    return database


# ============================================================
# DATABASE READINESS
# ============================================================

def check_database_readiness(
    database_path: Path | str | None = None,
) -> bool:
    """
    Verify that the configured SQLite database
    can be initialized, opened and queried.

    This check is intentionally lightweight and
    suitable for the /ready endpoint.
    """

    db_path = (
        Path(database_path)
        if database_path is not None
        else get_database_path()
    )

    try:
        # Ensure schema/database initialization succeeds.
        build_database(
            db_path
        )

        # Verify that SQLite can actually open and query
        # the configured database.
        with sqlite3.connect(
            str(db_path),
            timeout=1.0,
        ) as connection:

            result = connection.execute(
                "PRAGMA quick_check(1);"
            ).fetchone()

        return bool(
            result
            and result[0] == "ok"
        )

    except Exception:
        # Readiness checks must fail closed.
        #
        # Detailed logging will be added in the
        # observability hardening phase.
        return False


def get_database_readiness() -> bool:
    """
    FastAPI dependency provider used by /ready.
    """

    return check_database_readiness()


# ============================================================
# AUDIT REPOSITORY
# ============================================================

def build_audit_repository(
    database_path: Path | str | None = None,
) -> AuditRepository:
    """
    Build an AuditRepository backed by the
    configured SQLite database.
    """

    database = build_database(
        database_path
    )

    return AuditRepository(
        database
    )


# ============================================================
# AGENT RUNTIME
# ============================================================

def build_agent(
    database_path: Path | str | None = None,
) -> ControlledOrderAgent:
    """
    Build one fully wired production Agent runtime.
    """

    database = build_database(
        database_path
    )

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
        approval_repository=(
            approval_repository
        ),
    )


# ============================================================
# FASTAPI DEPENDENCIES
# ============================================================

def get_agent() -> ControlledOrderAgent:
    """
    FastAPI dependency provider for Agent runtimes.
    """

    return build_agent()


def get_audit_repository() -> AuditRepository:
    """
    FastAPI dependency provider for persisted
    execution traces.
    """

    return build_audit_repository()