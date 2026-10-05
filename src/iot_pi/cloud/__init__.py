"""Optional cloud telemetry bridge abstractions."""

from iot_pi.cloud.bridge import CloudTelemetryBridge
from iot_pi.cloud.errors import CloudDeliveryError
from iot_pi.cloud.interfaces import CloudTelemetrySink
from iot_pi.cloud.outbox import OutboxRecord, SQLiteTelemetryOutbox, TelemetryOutbox

__all__ = [
    "CloudDeliveryError",
    "CloudTelemetryBridge",
    "CloudTelemetrySink",
    "OutboxRecord",
    "SQLiteTelemetryOutbox",
    "TelemetryOutbox",
]
