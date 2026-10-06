"""Runtime integration for durable telemetry delivery."""

from __future__ import annotations

from iot_pi.cloud.bridge import CloudTelemetryBridge
from iot_pi.cloud.errors import CloudDeliveryError
from iot_pi.messaging.models import TelemetryMessage
from iot_pi.observability.health import HealthTracker


class DurableTelemetryRuntime:
    """Persist telemetry first, then deliver without blocking control failures."""

    def __init__(
        self,
        bridge: CloudTelemetryBridge,
        *,
        health: HealthTracker | None = None,
    ) -> None:
        """Create a runtime integration around a durable bridge."""
        self._bridge = bridge
        self._health = health

    @property
    def pending_count(self) -> int:
        """Return the current durable backlog size."""
        return self._bridge.pending_count

    def open(self) -> int:
        """Open durable storage, tolerate an offline sink, and drain if online."""
        connected = self._bridge.open(allow_sink_failure=True)
        self._sync_health()
        if not connected:
            return 0
        return self.drain()

    def enqueue(self, message: TelemetryMessage) -> int:
        """Persist one message and make one best-effort delivery attempt."""
        self._bridge.enqueue(message, auto_flush=False)
        self._sync_health()
        delivered = self._bridge.flush_opportunistically()
        self._sync_health()
        return delivered

    def drain(self) -> int:
        """Drain durable backlog using the bridge's configured retry policy."""
        delivered = 0
        while self._bridge.pending_count:
            try:
                count = self._bridge.flush()
            except CloudDeliveryError:
                break
            if count == 0:
                break
            delivered += count
            self._sync_health()

        self._sync_health()
        return delivered

    def close(self) -> None:
        """Close runtime resources without blocking on final network delivery."""
        self._sync_health()
        self._bridge.close(flush=False)

    def _sync_health(self) -> None:
        """Expose durable backlog size through runtime health."""
        if self._health is not None:
            self._health.set_backlog_size(self._bridge.pending_count)
