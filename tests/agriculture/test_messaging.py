"""Tests for smart-agriculture telemetry."""

from datetime import UTC, datetime

from iot_pi.agriculture.models import AgricultureObservation
from iot_pi.messaging.agriculture import agriculture_telemetry


def test_agriculture_telemetry_preserves_irrigation_state() -> None:
    """Telemetry should preserve the complete irrigation observation."""
    observation = AgricultureObservation(
        timestamp=datetime(2026, 10, 5, 12, 0, tzinfo=UTC),
        soil_moisture_percent=24.0,
        pump_on=True,
        reason="soil_dry",
        temperature_c=21.0,
        relative_humidity_percent=55.0,
    )

    message = agriculture_telemetry("farm-01", observation)

    assert message.device_id == "farm-01"
    assert message.event == "irrigation_observation"
    assert message.data["soil_moisture_percent"] == 24.0
    assert message.data["pump_on"] is True
