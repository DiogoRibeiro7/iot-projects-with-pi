"""Tests for runnable durable telemetry integration."""

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from iot_pi.cloud.bridge import CloudTelemetryBridge
from iot_pi.cloud.outbox import SQLiteTelemetryOutbox
from iot_pi.cloud.runtime import DurableTelemetryRuntime
from iot_pi.messaging.models import TelemetryMessage
from iot_pi.observability.health import HealthTracker


class ToggleSink:
    """Cloud sink that can transition between offline and online states."""

    def __init__(self, *, online: bool) -> None:
        self.online = online
        self.opened = False
        self.batches: list[tuple[TelemetryMessage, ...]] = []

    def open(self) -> None:
        """Open only when the simulated network is online."""
        if not self.online:
            raise OSError("broker unavailable")
        self.opened = True

    def close(self) -> None:
        """Record disconnection."""
        self.opened = False

    def send_batch(self, messages: Sequence[TelemetryMessage]) -> None:
        """Deliver or fail according to the simulated network state."""
        if not self.online:
            raise OSError("broker unavailable")
        self.batches.append(tuple(messages))


def message() -> TelemetryMessage:
    """Create one deterministic telemetry envelope."""
    return TelemetryMessage(
        device_id="weather-pi",
        event="weather_observation",
        timestamp=datetime(2026, 10, 6, 12, 0, tzinfo=UTC),
        data={"temperature_c": 21.0},
    )


def test_runtime_recovers_durable_backlog_after_restart(tmp_path: Path) -> None:
    """Offline telemetry should survive restart and drain when the sink returns."""
    path = tmp_path / "outbox.db"
    health = HealthTracker()
    offline = ToggleSink(online=False)
    first = DurableTelemetryRuntime(
        CloudTelemetryBridge(
            offline,
            batch_size=10,
            max_retries=1,
            outbox=SQLiteTelemetryOutbox(path),
        ),
        health=health,
    )

    assert first.open() == 0
    assert first.enqueue(message()) == 0
    assert first.pending_count == 1
    assert health.snapshot().backlog_size == 1
    first.close()

    online = ToggleSink(online=True)
    recovered_health = HealthTracker()
    second = DurableTelemetryRuntime(
        CloudTelemetryBridge(
            online,
            batch_size=10,
            max_retries=1,
            outbox=SQLiteTelemetryOutbox(path),
        ),
        health=recovered_health,
    )

    assert second.open() == 1
    assert second.pending_count == 0
    assert recovered_health.snapshot().backlog_size == 0
    assert online.batches == [(message(),)]
    second.close()
