"""Generic SQLite event and health persistence."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import sqlite3
from typing import Any


class SQLiteEventRepository:
    """Persist structured operational events and health snapshots."""

    def __init__(self, path: Path) -> None:
        """Create a repository for the given SQLite database."""
        self._path = path
        self._connection: sqlite3.Connection | None = None

    def open(self) -> None:
        """Open the database and initialize schema."""
        if self._connection is not None:
            return

        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path)
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    category TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.commit()
        except Exception:
            connection.close()
            raise

        self._connection = connection

    def close(self) -> None:
        """Commit pending work and close the connection."""
        if self._connection is not None:
            self._connection.commit()
            self._connection.close()
            self._connection = None

    def append(
        self,
        category: str,
        payload: dict[str, Any],
        *,
        timestamp: datetime | None = None,
    ) -> None:
        """Persist one structured event."""
        if self._connection is None:
            raise RuntimeError("event repository is not open")
        if not category.strip():
            raise ValueError("category must not be empty")

        event_time = timestamp or datetime.now(UTC)
        if event_time.tzinfo is None:
            raise ValueError("timestamp must include timezone information")

        self._connection.execute(
            "INSERT INTO events (timestamp, category, payload) VALUES (?, ?, ?)",
            (
                event_time.astimezone(UTC).isoformat(),
                category,
                json.dumps(payload, sort_keys=True, separators=(",", ":")),
            ),
        )
        self._connection.commit()

    def count(self) -> int:
        """Return the number of stored events."""
        if self._connection is None:
            raise RuntimeError("event repository is not open")

        row = self._connection.execute("SELECT COUNT(*) FROM events").fetchone()
        return 0 if row is None else int(row[0])

    def prune_older_than(
        self,
        retention: timedelta,
        *,
        now: datetime | None = None,
    ) -> int:
        """Delete events older than the configured retention window."""
        if self._connection is None:
            raise RuntimeError("event repository is not open")
        if retention <= timedelta(0):
            raise ValueError("retention must be greater than zero")

        reference = now or datetime.now(UTC)
        if reference.tzinfo is None:
            raise ValueError("now must include timezone information")

        cutoff = (reference - retention).astimezone(UTC).isoformat()
        cursor = self._connection.execute(
            "DELETE FROM events WHERE timestamp < ?",
            (cutoff,),
        )
        self._connection.commit()
        return int(cursor.rowcount)
