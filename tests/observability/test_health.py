"""Tests for runtime health tracking."""

from datetime import UTC, datetime

import pytest

from iot_pi.observability.health import HealthTracker


def test_health_tracker_records_success_failures_and_backlog() -> None:
    """Health snapshots should expose accumulated runtime state."""
    tracker = HealthTracker()
    timestamp = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

    tracker.record_success(timestamp=timestamp)
    tracker.record_sensor_failure()
    tracker.set_backlog_size(4)

    snapshot = tracker.snapshot()

    assert snapshot.sensor_failures == 1
    assert snapshot.last_successful_sample == timestamp
    assert snapshot.backlog_size == 4
    assert snapshot.uptime_seconds >= 0.0


def test_health_tracker_rejects_invalid_backlog() -> None:
    """Backlog size cannot be negative."""
    tracker = HealthTracker()

    with pytest.raises(ValueError, match="backlog"):
        tracker.set_backlog_size(-1)


def test_health_tracker_rejects_naive_timestamp() -> None:
    """Successful sample timestamps must be timezone-aware."""
    tracker = HealthTracker()

    with pytest.raises(ValueError, match="timezone"):
        tracker.record_success(timestamp=datetime(2026, 10, 1, 12, 0))
