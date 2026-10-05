"""Tests for the durable SQLite telemetry outbox."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from iot_pi.cloud.outbox import SQLiteTelemetryOutbox
from iot_pi.messaging.models import TelemetryMessage


def message(index: int) -> TelemetryMessage:
    """Create deterministic telemetry for outbox tests."""
    return TelemetryMessage(
        device_id="pi-01",
        event="weather_observation",
        timestamp=datetime(2026, 10, 5, 12, index, tzinfo=UTC),
        data={"temperature_c": 20.0 + index},
    )


def test_outbox_persists_messages_across_reopen(tmp_path: Path) -> None:
    """Pending telemetry should survive a process-style restart."""
    path = tmp_path / "outbox.db"
    first = SQLiteTelemetryOutbox(
        path,
        clock=lambda: datetime(2026, 10, 5, 13, 0, tzinfo=UTC),
    )
    first.open()
    record_id = first.enqueue(message(0))
    first.close()

    second = SQLiteTelemetryOutbox(path)
    second.open()
    try:
        records = second.peek(10)

        assert len(records) == 1
        assert records[0].record_id == record_id
        assert records[0].message == message(0)
        assert records[0].retry_count == 0
        assert second.count() == 1
    finally:
        second.close()


def test_outbox_acknowledges_exact_record_ids_atomically(tmp_path: Path) -> None:
    """Acknowledgement should remove only the delivered record IDs."""
    outbox = SQLiteTelemetryOutbox(tmp_path / "outbox.db")
    outbox.open()
    try:
        first_id = outbox.enqueue(message(0))
        second_id = outbox.enqueue(message(1))
        third_id = outbox.enqueue(message(2))

        deleted = outbox.acknowledge([first_id, third_id])

        assert deleted == 2
        assert tuple(record.record_id for record in outbox.peek(10)) == (second_id,)
    finally:
        outbox.close()


def test_outbox_tracks_retry_counts(tmp_path: Path) -> None:
    """Retry updates should apply only to selected pending records."""
    outbox = SQLiteTelemetryOutbox(tmp_path / "outbox.db")
    outbox.open()
    try:
        first_id = outbox.enqueue(message(0))
        outbox.enqueue(message(1))

        assert outbox.increment_retries([first_id]) == 1
        assert outbox.increment_retries([first_id]) == 1

        records = outbox.peek(10)
        assert records[0].retry_count == 2
        assert records[1].retry_count == 0
    finally:
        outbox.close()


def test_outbox_prunes_only_expired_records(tmp_path: Path) -> None:
    """Retention cleanup should leave recent pending telemetry intact."""
    path = tmp_path / "outbox.db"
    timestamps = iter(
        [
            datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
            datetime(2026, 10, 9, 12, 0, tzinfo=UTC),
        ]
    )
    outbox = SQLiteTelemetryOutbox(path, clock=lambda: next(timestamps))
    outbox.open()
    try:
        outbox.enqueue(message(0))
        outbox.enqueue(message(1))

        deleted = outbox.prune_older_than(
            timedelta(days=7),
            now=datetime(2026, 10, 10, 12, 0, tzinfo=UTC),
        )

        assert deleted == 1
        assert outbox.count() == 1
        assert outbox.peek(1)[0].message == message(1)
    finally:
        outbox.close()


def test_outbox_validates_lifecycle_and_arguments(tmp_path: Path) -> None:
    """Closed storage and invalid arguments should fail explicitly."""
    outbox = SQLiteTelemetryOutbox(tmp_path / "outbox.db")

    with pytest.raises(RuntimeError, match="not open"):
        outbox.count()

    outbox.open()
    outbox.open()
    try:
        assert outbox.acknowledge([]) == 0
        assert outbox.increment_retries([]) == 0

        with pytest.raises(ValueError, match="limit"):
            outbox.peek(0)
        with pytest.raises(ValueError, match="retention"):
            outbox.prune_older_than(timedelta(0))
        with pytest.raises(ValueError, match="timezone"):
            outbox.prune_older_than(
                timedelta(days=1),
                now=datetime(2026, 10, 10, 12, 0),
            )
    finally:
        outbox.close()
        outbox.close()


def test_outbox_rejects_naive_clock(tmp_path: Path) -> None:
    """Enqueue timestamps must be timezone-aware."""
    outbox = SQLiteTelemetryOutbox(
        tmp_path / "outbox.db",
        clock=lambda: datetime(2026, 10, 5, 12, 0),
    )
    outbox.open()
    try:
        with pytest.raises(ValueError, match="timezone-aware"):
            outbox.enqueue(message(0))
    finally:
        outbox.close()
