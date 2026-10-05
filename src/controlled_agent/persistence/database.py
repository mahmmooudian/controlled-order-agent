from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterator

from controlled_agent.persistence.schema import (
    SCHEMA_SQL,
)


class Database:
    """
    Lightweight SQLite database manager.

    Responsibilities:
    - Create database connections
    - Enable SQLite safety settings
    - Initialize the schema
    - Apply backward-compatible schema migrations
    - Provide transaction helpers

    No Agent business logic belongs here.
    """

    def __init__(
        self,
        db_path: str | Path,
    ) -> None:

        self.db_path = Path(
            db_path
        )

    def connect(
        self,
    ) -> sqlite3.Connection:
        """
        Open a configured SQLite connection.
        """

        if (
            str(self.db_path)
            != ":memory:"
        ):
            self.db_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

        connection = sqlite3.connect(
            str(self.db_path)
        )

        connection.row_factory = (
            sqlite3.Row
        )

        connection.execute(
            "PRAGMA foreign_keys = ON;"
        )

        return connection

    def initialize(
        self,
    ) -> None:
        """
        Create all database tables and indexes.

        Existing databases are upgraded using
        additive, backward-compatible migrations.

        Safe to execute multiple times.
        """

        with self.connect() as connection:

            connection.executescript(
                SCHEMA_SQL
            )

            self._migrate_approvals_schema(
                connection
            )

            self._create_approval_indexes(
                connection
            )

    # ========================================================
    # APPROVAL MIGRATION
    # ========================================================

    @staticmethod
    def _migrate_approvals_schema(
        connection: sqlite3.Connection,
    ) -> None:
        """
        Upgrade legacy approval tables.

        Older databases contain only:

            approval_id
            run_id
            action
            approved
            requested_at
            decided_at

        Security hardening adds:

            order_id
            context_hash
            consumed_at

        Legacy approval rows intentionally receive NULL
        context values. They therefore cannot authorize
        a new context-bound WRITE operation.
        """

        rows = connection.execute(
            """
            PRAGMA table_info(approvals);
            """
        ).fetchall()

        columns = {
            row["name"]
            for row in rows
        }

        migrations = (
            (
                "order_id",
                "TEXT",
            ),
            (
                "context_hash",
                "TEXT",
            ),
            (
                "consumed_at",
                "TEXT",
            ),
        )

        for (
            column_name,
            column_type,
        ) in migrations:

            if column_name in columns:
                continue

            connection.execute(
                (
                    "ALTER TABLE approvals "
                    f"ADD COLUMN {column_name} "
                    f"{column_type};"
                )
            )

    @staticmethod
    def _create_approval_indexes(
        connection: sqlite3.Connection,
    ) -> None:
        """
        Create indexes that depend on migrated columns.
        """

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_approvals_context
            ON approvals (
                run_id,
                action,
                order_id,
                context_hash
            );
            """
        )

        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
                uq_approvals_pending_context
            ON approvals (
                run_id,
                action,
                order_id,
                context_hash
            )
            WHERE approved IS NULL
              AND order_id IS NOT NULL
              AND context_hash IS NOT NULL;
            """
        )

    # ========================================================
    # INTROSPECTION
    # ========================================================

    def table_names(
        self,
    ) -> set[str]:
        """
        Return user-created SQLite table names.
        """

        with self.connect() as connection:

            rows = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                """
            ).fetchall()

        return {
            row["name"]
            for row in rows
        }

    def foreign_keys_enabled(
        self,
    ) -> bool:
        """
        Verify that foreign-key enforcement
        is enabled for new connections.
        """

        with self.connect() as connection:

            row = connection.execute(
                "PRAGMA foreign_keys;"
            ).fetchone()

        return bool(
            row[0]
        )