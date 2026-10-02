"""Tests for generic observability persistence."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from iot_pi.observability.storage import SQLiteEventRepository


def test_event_repository_persists_across_reopen(tmp_path: Path) -> None:
    """Events should survive process-style close and reopen cycles."""
    path = tmp_path / "events.db"
    repository = SQLiteEventRepository(path)

    repository.open()
    repository.append(
        "weather_sample",
        {"temperature_c": 21.5},
        timestamp=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
    )
    repository.close()

    reopened = SQLiteEventRepository(path)
    reopened.open()
    try:
        assert reopened.count() == 1
    finally:
        reopened.close()


def test_event_repository_prunes_expired_rows(tmp_path: Path) -> None:
    """Retention cleanup should delete only expired events."""
    repository = SQLiteEventRepository(tmp_path / "events.db")
    now = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)

    repository.open()
    try:
        repository.append(
            "old",
            {"value": 1},
            timestamp=now - timedelta(days=10),
        )
        repository.append(
            "recent",
            {"value": 2},
            timestamp=now - timedelta(days=1),
        )

        deleted = repository.prune_older_than(timedelta(days=7), now=now)

        assert deleted == 1
        assert repository.count() == 1
    finally:
        repository.close()
