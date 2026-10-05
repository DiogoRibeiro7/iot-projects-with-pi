"""Tests for cloud telemetry batching and retry behavior."""

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from iot_pi.cloud.bridge import CloudTelemetryBridge
from iot_pi.cloud.errors import CloudDeliveryError
from iot_pi.messaging.models import TelemetryMessage


class FakeCloudSink:
    """Cloud sink test double with configurable transient failures."""

    def __init__(self, failures_before_success: int = 0) -> None:
        self.failures_before_success = failures_before_success
        self.opened = False
        self.closed = False
        self.attempts = 0
        self.batches: list[tuple[TelemetryMessage, ...]] = []

    def open(self) -> None:
        """Record transport initialization."""
        self.opened = True

    def close(self) -> None:
        """Record transport shutdown."""
        self.closed = True

    def send_batch(self, messages: Sequence[TelemetryMessage]) -> None:
        """Fail transiently or capture the delivered batch."""
        self.attempts += 1
        if self.attempts <= self.failures_before_success:
            raise RuntimeError("temporary cloud failure")
        self.batches.append(tuple(messages))


def message(index: int) -> TelemetryMessage:
    """Create deterministic telemetry for bridge tests."""
    return TelemetryMessage(
        device_id="pi-01",
        event="weather_observation",
        timestamp=datetime(2026, 10, 5, 12, index, tzinfo=UTC),
        data={"temperature_c": 20.0 + index},
    )


def test_bridge_flushes_when_batch_size_is_reached() -> None:
    """A full batch should be delivered automatically."""
    sink = FakeCloudSink()
    bridge = CloudTelemetryBridge(sink, batch_size=2)

    assert bridge.enqueue(message(0)) == 0
    assert bridge.pending_count == 1
    assert bridge.enqueue(message(1)) == 2

    assert bridge.pending_count == 0
    assert len(sink.batches) == 1
    assert sink.batches[0] == (message(0), message(1))


def test_bridge_retries_with_exponential_backoff() -> None:
    """Transient failures should use bounded exponential backoff."""
    sink = FakeCloudSink(failures_before_success=2)
    sleeps: list[float] = []
    bridge = CloudTelemetryBridge(
        sink,
        batch_size=10,
        max_retries=3,
        backoff_seconds=0.5,
        sleeper=sleeps.append,
    )
    bridge.enqueue(message(0))

    delivered = bridge.flush()

    assert delivered == 1
    assert sink.attempts == 3
    assert sleeps == [0.5, 1.0]
    assert bridge.pending_count == 0


def test_bridge_preserves_pending_batch_after_retry_exhaustion() -> None:
    """A failed batch must remain pending instead of being silently dropped."""
    sink = FakeCloudSink(failures_before_success=10)
    bridge = CloudTelemetryBridge(
        sink,
        max_retries=2,
        backoff_seconds=0.01,
        sleeper=lambda _: None,
    )
    bridge.enqueue(message(0))

    with pytest.raises(CloudDeliveryError, match="after 2 attempts"):
        bridge.flush()

    assert bridge.pending_count == 1


def test_bridge_lifecycle_flushes_before_close() -> None:
    """Closing should flush buffered telemetry before releasing the sink."""
    sink = FakeCloudSink()
    bridge = CloudTelemetryBridge(sink, batch_size=10)
    bridge.open()
    bridge.enqueue(message(0))

    bridge.close()

    assert sink.opened is True
    assert sink.closed is True
    assert len(sink.batches) == 1


@pytest.mark.parametrize(
    ("batch_size", "max_retries", "backoff_seconds"),
    [(0, 1, 1.0), (1, 0, 1.0), (1, 1, 0.0)],
)
def test_bridge_rejects_invalid_retry_configuration(
    batch_size: int,
    max_retries: int,
    backoff_seconds: float,
) -> None:
    """Batching and retry controls must be strictly positive."""
    with pytest.raises(ValueError):
        CloudTelemetryBridge(
            FakeCloudSink(),
            batch_size=batch_size,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
        )
