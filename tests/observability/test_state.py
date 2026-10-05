"""Tests for health snapshot persistence and retained MQTT state."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from iot_pi.messaging.fake import InMemoryPublisher
from iot_pi.observability.health import HealthSnapshot, HealthTracker
from iot_pi.observability.state import (
    CompositeHealthObserver,
    HealthStateFile,
    MqttHealthStatePublisher,
)


def snapshot() -> HealthSnapshot:
    """Create a deterministic health snapshot."""
    return HealthSnapshot(
        uptime_seconds=12.5,
        sensor_failures=2,
        last_successful_sample=datetime(2026, 10, 5, 21, 0, tzinfo=UTC),
        backlog_size=4,
    )


def test_health_state_file_round_trips_snapshot(tmp_path: Path) -> None:
    """The local health file should preserve the stable JSON schema."""
    state = HealthStateFile(tmp_path / "health.json")

    state(snapshot())

    assert state.read() == snapshot()
    assert not (tmp_path / "health.json.tmp").exists()


def test_mqtt_health_state_is_retained() -> None:
    """Health publishing should use the retained device-state topic."""
    publisher = InMemoryPublisher()
    observer = MqttHealthStatePublisher(
        publisher,
        device_id="pi-01",
        qos=1,
    )

    observer(snapshot())

    message = publisher.messages[0]
    assert message.topic == "iot/pi-01/state/health"
    assert message.qos == 1
    assert message.retain is True
    assert '"sensor_failures":2' in message.payload


@pytest.mark.parametrize(
    ("device_id", "qos"),
    [("", 1), ("pi-01", -1), ("pi-01", 3)],
)
def test_mqtt_health_state_validates_configuration(
    device_id: str,
    qos: int,
) -> None:
    """Invalid health publisher configuration should fail early."""
    with pytest.raises(ValueError):
        MqttHealthStatePublisher(
            InMemoryPublisher(),
            device_id=device_id,
            qos=qos,
        )


def test_composite_health_observer_calls_every_sink() -> None:
    """Composite observers should receive the same snapshot."""
    received: list[HealthSnapshot] = []
    observer = CompositeHealthObserver(
        received.append,
        received.append,
    )

    observer(snapshot())

    assert received == [snapshot(), snapshot()]



def test_health_tracker_updates_state_file(tmp_path: Path) -> None:
    """A tracker observer should persist live state after each mutation."""
    state = HealthStateFile(tmp_path / "health.json")
    tracker = HealthTracker(observer=state)

    tracker.record_sensor_failure()
    tracker.set_backlog_size(3)

    persisted = state.read()

    assert persisted.sensor_failures == 1
    assert persisted.backlog_size == 3
