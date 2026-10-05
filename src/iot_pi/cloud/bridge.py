"""Batching and retry orchestration for cloud telemetry."""

from __future__ import annotations

import time
from collections.abc import Callable

from iot_pi.cloud.errors import CloudDeliveryError
from iot_pi.cloud.interfaces import CloudTelemetrySink
from iot_pi.messaging.models import TelemetryMessage

Sleeper = Callable[[float], None]


class CloudTelemetryBridge:
    """Buffer telemetry and forward it through a cloud sink with retries."""

    def __init__(
        self,
        sink: CloudTelemetrySink,
        *,
        batch_size: int = 10,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
        sleeper: Sleeper | None = None,
    ) -> None:
        """Create a cloud telemetry bridge."""
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero")
        if max_retries <= 0:
            raise ValueError("max_retries must be greater than zero")
        if backoff_seconds <= 0:
            raise ValueError("backoff_seconds must be greater than zero")

        self._sink = sink
        self._batch_size = batch_size
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._sleeper = sleeper or time.sleep
        self._pending: list[TelemetryMessage] = []

    @property
    def pending_count(self) -> int:
        """Return the number of telemetry messages waiting for delivery."""
        return len(self._pending)

    def open(self) -> None:
        """Initialize the underlying cloud sink."""
        self._sink.open()

    def close(self) -> None:
        """Flush pending telemetry and close the underlying sink."""
        try:
            if self._pending:
                self.flush()
        finally:
            self._sink.close()

    def enqueue(self, message: TelemetryMessage) -> int:
        """Buffer one message and flush automatically when the batch is full."""
        self._pending.append(message)
        if len(self._pending) >= self._batch_size:
            return self.flush()
        return 0

    def flush(self) -> int:
        """Deliver the current batch with bounded exponential backoff."""
        if not self._pending:
            return 0

        batch = tuple(self._pending)
        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                self._sink.send_batch(batch)
            except Exception as exc:
                last_error = exc
                if attempt < self._max_retries - 1:
                    self._sleeper(self._backoff_seconds * (2**attempt))
                continue

            del self._pending[: len(batch)]
            return len(batch)

        raise CloudDeliveryError(
            f"unable to deliver telemetry after {self._max_retries} attempts"
        ) from last_error
