"""Typed cloud telemetry interfaces."""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from iot_pi.messaging.models import TelemetryMessage


@runtime_checkable
class CloudTelemetrySink(Protocol):
    """Transport boundary for forwarding telemetry to an external service."""

    def open(self) -> None:
        """Initialize the cloud transport."""

    def close(self) -> None:
        """Release the cloud transport."""

    def send_batch(self, messages: Sequence[TelemetryMessage]) -> None:
        """Deliver one ordered telemetry batch."""
