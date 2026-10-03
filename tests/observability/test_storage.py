"""Tests for generic observability persistence."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

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



def test_event_repository_validates_open_state_and_event_input(
    tmp_path: Path,
) -> None:
    """Repository methods should reject invalid lifecycle and event inputs."""
    repository = SQLiteEventRepository(tmp_path / "events.db")

    with pytest.raises(RuntimeError, match="not open"):
        repository.append("event", {})
    with pytest.raises(RuntimeError, match="not open"):
        repository.count()
    with pytest.raises(RuntimeError, match="not open"):
        repository.prune_older_than(timedelta(days=1))

    repository.open()
    repository.open()
    try:
        with pytest.raises(ValueError, match="category"):
            repository.append("   ", {})
        with pytest.raises(ValueError, match="timezone"):
            repository.append(
                "event",
                {},
                timestamp=datetime(2026, 10, 3, 12, 0),
            )
        with pytest.raises(ValueError, match="retention"):
            repository.prune_older_than(timedelta(0))
        with pytest.raises(ValueError, match="timezone"):
            repository.prune_older_than(
                timedelta(days=1),
                now=datetime(2026, 10, 3, 12, 0),
            )
    finally:
        repository.close()
        repository.close()
