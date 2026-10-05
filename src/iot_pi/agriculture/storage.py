"""SQLite persistence for smart-agriculture observations."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from iot_pi.agriculture.models import AgricultureObservation


class SQLiteAgricultureStore:
    """Persist irrigation observations in SQLite."""

    def __init__(self, path: Path) -> None:
        """Create a store targeting the given database path."""
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
                CREATE TABLE IF NOT EXISTS agriculture_observations (
                    timestamp TEXT NOT NULL,
                    soil_moisture_percent REAL NOT NULL,
                    pump_on INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    temperature_c REAL,
                    relative_humidity_percent REAL
                )
                """
            )
            connection.commit()
        except Exception:
            connection.close()
            raise

        self._connection = connection

    def close(self) -> None:
        """Commit outstanding work and close the connection."""
        if self._connection is not None:
            self._connection.commit()
            self._connection.close()
            self._connection = None

    def save(self, observation: AgricultureObservation) -> None:
        """Persist one agriculture observation."""
        if self._connection is None:
            raise RuntimeError("agriculture store is not open")

        self._connection.execute(
            """
            INSERT INTO agriculture_observations (
                timestamp,
                soil_moisture_percent,
                pump_on,
                reason,
                temperature_c,
                relative_humidity_percent
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                observation.timestamp.isoformat(),
                observation.soil_moisture_percent,
                int(observation.pump_on),
                observation.reason,
                observation.temperature_c,
                observation.relative_humidity_percent,
            ),
        )
        self._connection.commit()

    def count(self) -> int:
        """Return the number of persisted observations."""
        if self._connection is None:
            raise RuntimeError("agriculture store is not open")

        row = self._connection.execute(
            "SELECT COUNT(*) FROM agriculture_observations"
        ).fetchone()
        return 0 if row is None else int(row[0])

    def latest(self) -> AgricultureObservation | None:
        """Return the latest persisted observation."""
        if self._connection is None:
            raise RuntimeError("agriculture store is not open")

        row = self._connection.execute(
            """
            SELECT
                timestamp,
                soil_moisture_percent,
                pump_on,
                reason,
                temperature_c,
                relative_humidity_percent
            FROM agriculture_observations
            ORDER BY rowid DESC
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            return None

        return AgricultureObservation(
            timestamp=datetime.fromisoformat(str(row[0])),
            soil_moisture_percent=float(row[1]),
            pump_on=bool(row[2]),
            reason=str(row[3]),
            temperature_c=None if row[4] is None else float(row[4]),
            relative_humidity_percent=None if row[5] is None else float(row[5]),
        )
