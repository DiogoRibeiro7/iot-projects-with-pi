"""Durable telemetry outbox abstractions and SQLite implementation."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol

from iot_pi.messaging.models import TelemetryMessage

Clock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class OutboxRecord:
    """One persisted telemetry message awaiting acknowledgement."""

    record_id: int
    message: TelemetryMessage
    retry_count: int
    created_at: datetime


class TelemetryOutbox(Protocol):
    """Storage boundary used by the cloud bridge for durable buffering."""

    def open(self) -> None:
        """Initialize outbox storage."""

    def close(self) -> None:
        """Release outbox storage."""

    def enqueue(self, message: TelemetryMessage) -> int:
        """Persist one telemetry message and return its record identifier."""

    def peek(self, limit: int) -> tuple[OutboxRecord, ...]:
        """Return the oldest pending records without removing them."""

    def acknowledge(self, record_ids: Sequence[int]) -> int:
        """Delete delivered records atomically."""

    def increment_retries(self, record_ids: Sequence[int]) -> int:
        """Increment retry counters atomically."""

    def count(self) -> int:
        """Return the number of pending records."""


class SQLiteTelemetryOutbox:
    """Persist pending telemetry in a local SQLite database."""

    def __init__(
        self,
        path: Path,
        *,
        clock: Clock | None = None,
    ) -> None:
        """Create an outbox targeting the given SQLite path."""
        self._path = path
        self._clock = clock or (lambda: datetime.now(UTC))
        self._connection: sqlite3.Connection | None = None

    def open(self) -> None:
        """Open the database and initialize the outbox schema."""
        if self._connection is not None:
            return

        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path)
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS telemetry_outbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_telemetry_outbox_created_at
                ON telemetry_outbox (created_at, id)
                """
            )
            connection.commit()
        except Exception:
            connection.close()
            raise

        self._connection = connection

    def close(self) -> None:
        """Commit pending work and close the database."""
        if self._connection is not None:
            self._connection.commit()
            self._connection.close()
            self._connection = None

    def enqueue(self, message: TelemetryMessage) -> int:
        """Persist one telemetry message."""
        connection = self._require_connection()
        created_at = self._clock()
        if created_at.tzinfo is None:
            raise ValueError("outbox clock must return a timezone-aware datetime")

        with connection:
            cursor = connection.execute(
                """
                INSERT INTO telemetry_outbox (created_at, payload, retry_count)
                VALUES (?, ?, 0)
                """,
                (
                    created_at.astimezone(UTC).isoformat(),
                    message.to_json(),
                ),
            )

        if cursor.lastrowid is None:
            raise RuntimeError("SQLite did not return an outbox record id")
        return int(cursor.lastrowid)

    def peek(self, limit: int) -> tuple[OutboxRecord, ...]:
        """Return the oldest pending telemetry records."""
        if limit <= 0:
            raise ValueError("limit must be greater than zero")

        connection = self._require_connection()
        rows = connection.execute(
            """
            SELECT id, payload, retry_count, created_at
            FROM telemetry_outbox
            ORDER BY id
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return tuple(
            OutboxRecord(
                record_id=int(row[0]),
                message=TelemetryMessage.from_json(str(row[1])),
                retry_count=int(row[2]),
                created_at=datetime.fromisoformat(str(row[3])),
            )
            for row in rows
        )

    def acknowledge(self, record_ids: Sequence[int]) -> int:
        """Delete delivered records in one transaction."""
        if not record_ids:
            return 0

        connection = self._require_connection()
        placeholders = ",".join("?" for _ in record_ids)
        with connection:
            cursor = connection.execute(
                f"DELETE FROM telemetry_outbox WHERE id IN ({placeholders})",
                tuple(record_ids),
            )
        return int(cursor.rowcount)

    def increment_retries(self, record_ids: Sequence[int]) -> int:
        """Increment retry counters in one transaction."""
        if not record_ids:
            return 0

        connection = self._require_connection()
        placeholders = ",".join("?" for _ in record_ids)
        with connection:
            cursor = connection.execute(
                (
                    "UPDATE telemetry_outbox "
                    "SET retry_count = retry_count + 1 "
                    f"WHERE id IN ({placeholders})"
                ),
                tuple(record_ids),
            )
        return int(cursor.rowcount)

    def count(self) -> int:
        """Return the number of pending telemetry records."""
        connection = self._require_connection()
        row = connection.execute("SELECT COUNT(*) FROM telemetry_outbox").fetchone()
        return 0 if row is None else int(row[0])

    def prune_older_than(
        self,
        retention: timedelta,
        *,
        now: datetime | None = None,
    ) -> int:
        """Delete pending records older than the configured retention window."""
        if retention <= timedelta(0):
            raise ValueError("retention must be greater than zero")

        reference = now or datetime.now(UTC)
        if reference.tzinfo is None:
            raise ValueError("now must include timezone information")

        connection = self._require_connection()
        cutoff = (reference - retention).astimezone(UTC).isoformat()
        with connection:
            cursor = connection.execute(
                "DELETE FROM telemetry_outbox WHERE created_at < ?",
                (cutoff,),
            )
        return int(cursor.rowcount)

    def _require_connection(self) -> sqlite3.Connection:
        """Return the open connection or fail with a clear lifecycle error."""
        if self._connection is None:
            raise RuntimeError("telemetry outbox is not open")
        return self._connection
