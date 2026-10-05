"""Smart-agriculture telemetry helpers."""

from iot_pi.agriculture.models import AgricultureObservation
from iot_pi.messaging.models import TelemetryMessage


def agriculture_telemetry(
    device_id: str,
    observation: AgricultureObservation,
) -> TelemetryMessage:
    """Build a typed telemetry envelope for an irrigation observation."""
    return TelemetryMessage(
        device_id=device_id,
        event="irrigation_observation",
        timestamp=observation.timestamp,
        data={
            "soil_moisture_percent": observation.soil_moisture_percent,
            "pump_on": observation.pump_on,
            "reason": observation.reason,
            "temperature_c": observation.temperature_c,
            "relative_humidity_percent": observation.relative_humidity_percent,
        },
    )
