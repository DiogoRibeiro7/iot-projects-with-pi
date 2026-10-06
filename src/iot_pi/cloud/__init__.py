"""Optional cloud telemetry bridge abstractions."""

from iot_pi.cloud.bridge import CloudTelemetryBridge
from iot_pi.cloud.errors import CloudDeliveryError
from iot_pi.cloud.interfaces import CloudTelemetrySink
from iot_pi.cloud.outbox import OutboxRecord, SQLiteTelemetryOutbox, TelemetryOutbox
from iot_pi.cloud.runtime import DurableTelemetryRuntime

__all__ = [
    "CloudDeliveryError",
    "CloudTelemetryBridge",
    "CloudTelemetrySink",
    "DurableTelemetryRuntime",
    "OutboxRecord",
    "SQLiteTelemetryOutbox",
    "TelemetryOutbox",
]
