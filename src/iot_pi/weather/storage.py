"""SQLite persistence for weather observations."""

from pathlib import Path
import sqlite3

from iot_pi.weather.models import WeatherObservation


class SQLiteWeatherStore:
    """Persist weather observations in a local SQLite database."""

    def __init__(self, path: Path) -> None:
        """Create a weather store targeting the given database path."""
        self._path = path
        self._connection: sqlite3.Connection | None = None

    def open(self) -> None:
        """Open the database and create the schema if needed."""
        if self._connection is not None:
            return

        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self._path)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS weather_observations (
                timestamp TEXT NOT NULL,
                temperature_c REAL NOT NULL,
                relative_humidity_percent REAL NOT NULL,
                pressure_hpa REAL
            )
            """
        )
        self._connection.commit()

    def close(self) -> None:
        """Commit outstanding work and close the database connection."""
        if self._connection is not None:
            self._connection.commit()
            self._connection.close()
            self._connection = None

    def save(self, observation: WeatherObservation) -> None:
        """Persist one validated observation."""
        if self._connection is None:
            raise RuntimeError("weather store is not open")

        self._connection.execute(
            """
            INSERT INTO weather_observations (
                timestamp,
                temperature_c,
                relative_humidity_percent,
                pressure_hpa
            ) VALUES (?, ?, ?, ?)
            """,
            (
                observation.timestamp.isoformat(),
                observation.temperature_c,
                observation.relative_humidity_percent,
                observation.pressure_hpa,
            ),
        )
        self._connection.commit()

    def count(self) -> int:
        """Return the number of persisted observations."""
        if self._connection is None:
            raise RuntimeError("weather store is not open")

        row = self._connection.execute(
            "SELECT COUNT(*) FROM weather_observations"
        ).fetchone()
        if row is None:
            return 0
        return int(row[0])
