"""Integration tests for CloudTelemetryBridge with SQLite durability."""

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest

from iot_pi.cloud.bridge import CloudTelemetryBridge
from iot_pi.cloud.errors import CloudDeliveryError
from iot_pi.cloud.outbox import SQLiteTelemetryOutbox
from iot_pi.messaging.models import TelemetryMessage


class CapturingSink:
    """Capture delivered cloud batches with configurable transient failure."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.opened = False
        self.closed = False
        self.batches: list[tuple[TelemetryMessage, ...]] = []

    def open(self) -> None:
        self.opened = True

    def close(self) -> None:
        self.closed = True

    def send_batch(self, messages: Sequence[TelemetryMessage]) -> None:
        if self.fail:
            raise RuntimeError("cloud unavailable")
        self.batches.append(tuple(messages))


def message(index: int) -> TelemetryMessage:
    """Create deterministic telemetry for durable bridge tests."""
    return TelemetryMessage(
        device_id="pi-01",
        event="weather_observation",
        timestamp=datetime(2026, 10, 5, 14, index, tzinfo=UTC),
        data={"temperature_c": 20.0 + index},
    )


def test_failed_batch_survives_restart_and_is_acknowledged(
    tmp_path: Path,
) -> None:
    """Pending telemetry should survive one bridge process and replay in another."""
    path = tmp_path / "outbox.db"
    failing = CapturingSink(fail=True)
    first = CloudTelemetryBridge(
        failing,
        batch_size=2,
        max_retries=1,
        outbox=SQLiteTelemetryOutbox(path),
    )
    first.open()

    first.enqueue(message(0))
    with pytest.raises(CloudDeliveryError):
        first.enqueue(message(1))

    assert first.pending_count == 2

    failing.fail = False
    first._sink.close()
    first._outbox.close()  # type: ignore[union-attr]

    succeeding = CapturingSink()
    second = CloudTelemetryBridge(
        succeeding,
        batch_size=2,
        outbox=SQLiteTelemetryOutbox(path),
    )
    second.open()
    try:
        assert second.pending_count == 2

        delivered = second.flush()

        assert delivered == 2
        assert second.pending_count == 0
        assert succeeding.batches == [(message(0), message(1))]
    finally:
        second.close()


def test_durable_bridge_increments_retry_count_on_failure(
    tmp_path: Path,
) -> None:
    """Each failed delivery attempt should be persisted in the outbox."""
    path = tmp_path / "outbox.db"
    outbox = SQLiteTelemetryOutbox(path)
    bridge = CloudTelemetryBridge(
        CapturingSink(fail=True),
        batch_size=10,
        max_retries=2,
        backoff_seconds=0.01,
        sleeper=lambda _: None,
        outbox=outbox,
    )
    bridge.open()
    bridge.enqueue(message(0))

    with pytest.raises(CloudDeliveryError):
        bridge.flush()

    records = outbox.peek(10)
    assert records[0].retry_count == 2

    bridge._sink.fail = False  # type: ignore[attr-defined]
    bridge.flush()
    bridge.close()


def test_durable_bridge_open_rolls_back_outbox_when_sink_fails(
    tmp_path: Path,
) -> None:
    """A sink initialization failure should not leave the outbox connection open."""
    class FailingOpenSink(CapturingSink):
        def open(self) -> None:
            raise RuntimeError("sink init failed")

    outbox = SQLiteTelemetryOutbox(tmp_path / "outbox.db")
    bridge = CloudTelemetryBridge(FailingOpenSink(), outbox=outbox)

    with pytest.raises(RuntimeError, match="sink init failed"):
        bridge.open()

    with pytest.raises(RuntimeError, match="not open"):
        outbox.count()
