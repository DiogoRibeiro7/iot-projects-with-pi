"""Tests for runtime health tracking."""

from datetime import UTC, datetime

import pytest

from iot_pi.observability.health import HealthSnapshot, HealthTracker


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


def test_health_snapshot_round_trips_json() -> None:
    """The stable health schema should round-trip through JSON."""
    original = HealthSnapshot(
        uptime_seconds=12.5,
        sensor_failures=2,
        last_successful_sample=datetime(2026, 10, 5, 21, 0, tzinfo=UTC),
        backlog_size=4,
    )

    restored = HealthSnapshot.from_json(original.to_json())

    assert restored == original


@pytest.mark.parametrize(
    "payload",
    [
        "[]",
        '{"uptime_seconds":"bad","sensor_failures":0,"last_successful_sample":null,"backlog_size":0}',
        '{"uptime_seconds":1,"sensor_failures":true,"last_successful_sample":null,"backlog_size":0}',
        '{"uptime_seconds":1,"sensor_failures":0,"last_successful_sample":null,"backlog_size":true}',
        '{"uptime_seconds":1,"sensor_failures":0,"last_successful_sample":42,"backlog_size":0}',
        '{"uptime_seconds":1,"sensor_failures":0,"last_successful_sample":"2026-10-05T21:00:00","backlog_size":0}',
    ],
)
def test_health_snapshot_rejects_invalid_json(payload: str) -> None:
    """Malformed health-state payloads should fail explicitly."""
    with pytest.raises(ValueError):
        HealthSnapshot.from_json(payload)


@pytest.mark.parametrize(
    "uptime_seconds",
    [-1.0, float("nan"), float("inf")],
)
def test_health_snapshot_rejects_invalid_uptime(uptime_seconds: float) -> None:
    """Uptime must be finite and non-negative."""
    with pytest.raises(ValueError, match="uptime_seconds"):
        HealthSnapshot(
            uptime_seconds=uptime_seconds,
            sensor_failures=0,
            last_successful_sample=None,
            backlog_size=0,
        )


def test_health_tracker_emits_after_each_mutation() -> None:
    """Configured observers should receive current snapshots after updates."""
    received: list[HealthSnapshot] = []
    tracker = HealthTracker(observer=received.append)
    timestamp = datetime(2026, 10, 5, 21, 0, tzinfo=UTC)

    tracker.record_success(timestamp=timestamp)
    tracker.record_sensor_failure()
    tracker.set_backlog_size(3)

    assert len(received) == 3
    assert received[-1].sensor_failures == 1
    assert received[-1].last_successful_sample == timestamp
    assert received[-1].backlog_size == 3
