from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterator

from controlled_agent.persistence.schema import SCHEMA_SQL


class Database:
    """
    Lightweight SQLite database manager.

    Responsibilities:
    - Create database connections
    - Enable SQLite safety settings
    - Initialize the schema
    - Provide transaction helpers

    No Agent business logic belongs here.
    """

    def __init__(
        self,
        db_path: str | Path,
    ) -> None:

        self.db_path = Path(db_path)

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

        connection.row_factory = sqlite3.Row

        connection.execute(
            "PRAGMA foreign_keys = ON;"
        )

        return connection

    def initialize(
        self,
    ) -> None:
        """
        Create all database tables and indexes.
        Safe to execute multiple times.
        """

        with self.connect() as connection:
            connection.executescript(
                SCHEMA_SQL
            )

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

        return bool(row[0])