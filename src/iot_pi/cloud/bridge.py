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
        self._sink_open = False

    @property
    def pending_count(self) -> int:
        """Return the number of telemetry messages waiting for delivery."""
        if self._outbox is not None:
            return self._outbox.count()
        return len(self._pending)

    def open(self, *, allow_sink_failure: bool = False) -> bool:
        """Initialize storage and sink, optionally remaining usable offline."""
        if self._outbox is not None:
            self._outbox.open()

        try:
            self._ensure_sink_open()
        except Exception:
            if allow_sink_failure and self._outbox is not None:
                return False
            if self._outbox is not None:
                self._outbox.close()
            raise

        return True

    def close(self, *, flush: bool = True) -> None:
        """Optionally flush pending telemetry and close resources."""
        try:
            if flush and self._sink_open and self.pending_count:
                self.flush()
        finally:
            try:
                self._disconnect_sink()
            finally:
                if self._outbox is not None:
                    self._outbox.close()

    def enqueue(
        self,
        message: TelemetryMessage,
        *,
        auto_flush: bool = True,
    ) -> int:
        """Buffer one message and optionally flush when the batch is full."""
        if self._outbox is not None:
            self._outbox.enqueue(message)
        else:
            self._pending.append(message)

        if auto_flush and self.pending_count >= self._batch_size:
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
                self._ensure_sink_open()
                self._sink.send_batch(messages)
            except Exception as exc:
                last_error = exc
                if self._outbox is not None:
                    self._outbox.increment_retries(record_ids)
                self._disconnect_sink()
                if attempt < self._max_retries - 1:
                    self._sleeper(self._backoff_seconds * (2**attempt))
                continue

            self._acknowledge(messages, record_ids)
            return len(messages)

        raise CloudDeliveryError(
            f"unable to deliver telemetry after {self._max_retries} attempts"
        ) from last_error

    def flush_opportunistically(self) -> int:
        """Attempt one batch without retry sleeps or propagating network errors."""
        messages, record_ids = self._next_batch()
        if not messages:
            return 0

        try:
            self._ensure_sink_open()
            self._sink.send_batch(messages)
        except Exception:
            if self._outbox is not None:
                self._outbox.increment_retries(record_ids)
            self._disconnect_sink()
            return 0

        self._acknowledge(messages, record_ids)
        return len(messages)

    def _acknowledge(
        self,
        messages: tuple[TelemetryMessage, ...],
        record_ids: tuple[int, ...],
    ) -> None:
        """Remove a successfully delivered batch from its buffer."""
        if self._outbox is not None:
            self._outbox.acknowledge(record_ids)
        else:
            del self._pending[: len(messages)]

    def _ensure_sink_open(self) -> None:
        """Open the sink only when it is currently disconnected."""
        if self._sink_open:
            return
        self._sink.open()
        self._sink_open = True

    def _disconnect_sink(self) -> None:
        """Close the sink when connected and reset connection state."""
        if self._sink_open:
            try:
                self._sink.close()
            finally:
                self._sink_open = False

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
