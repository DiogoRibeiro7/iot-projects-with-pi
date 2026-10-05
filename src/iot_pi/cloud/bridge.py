"""Batching and retry orchestration for cloud telemetry."""

from __future__ import annotations

import time
from collections.abc import Callable

from iot_pi.cloud.errors import CloudDeliveryError
from iot_pi.cloud.interfaces import CloudTelemetrySink
from iot_pi.cloud.outbox import TelemetryOutbox
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
        outbox: TelemetryOutbox | None = None,
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
        self._outbox = outbox
        self._pending: list[TelemetryMessage] = []

    @property
    def pending_count(self) -> int:
        """Return the number of telemetry messages waiting for delivery."""
        if self._outbox is not None:
            return self._outbox.count()
        return len(self._pending)

    def open(self) -> None:
        """Initialize the underlying cloud sink and optional outbox."""
        if self._outbox is not None:
            self._outbox.open()
        try:
            self._sink.open()
        except Exception:
            if self._outbox is not None:
                self._outbox.close()
            raise

    def close(self) -> None:
        """Flush pending telemetry and close resources."""
        try:
            if self.pending_count:
                self.flush()
        finally:
            try:
                self._sink.close()
            finally:
                if self._outbox is not None:
                    self._outbox.close()

    def enqueue(self, message: TelemetryMessage) -> int:
        """Buffer one message and flush automatically when the batch is full."""
        if self._outbox is not None:
            self._outbox.enqueue(message)
        else:
            self._pending.append(message)

        if self.pending_count >= self._batch_size:
            return self.flush()
        return 0

    def flush(self) -> int:
        """Deliver the current batch with bounded exponential backoff."""
        messages, record_ids = self._next_batch()
        if not messages:
            return 0

        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                self._sink.send_batch(messages)
            except Exception as exc:
                last_error = exc
                if self._outbox is not None:
                    self._outbox.increment_retries(record_ids)
                if attempt < self._max_retries - 1:
                    self._sleeper(self._backoff_seconds * (2**attempt))
                continue

            if self._outbox is not None:
                self._outbox.acknowledge(record_ids)
            else:
                del self._pending[: len(messages)]
            return len(messages)

        raise CloudDeliveryError(
            f"unable to deliver telemetry after {self._max_retries} attempts"
        ) from last_error

    def _next_batch(self) -> tuple[tuple[TelemetryMessage, ...], tuple[int, ...]]:
        """Load the next in-memory or durable batch."""
        if self._outbox is not None:
            records = self._outbox.peek(self._batch_size)
            return (
                tuple(record.message for record in records),
                tuple(record.record_id for record in records),
            )

        messages = tuple(self._pending[: self._batch_size])
        return messages, ()
