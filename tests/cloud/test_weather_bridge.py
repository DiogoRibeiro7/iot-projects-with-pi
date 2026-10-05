"""Integration tests for weather telemetry and cloud sinks."""

from datetime import UTC, datetime

from iot_pi.cloud.bridge import CloudTelemetryBridge
from iot_pi.messaging.models import TelemetryMessage
from iot_pi.messaging.weather import weather_telemetry
from iot_pi.weather.models import WeatherObservation


class CapturingSink:
    """Capture cloud batches for integration tests."""

    def __init__(self) -> None:
        self.messages: list[TelemetryMessage] = []

    def open(self) -> None:
        """Initialize the fake sink."""

    def close(self) -> None:
        """Release the fake sink."""

    def send_batch(self, messages: tuple[TelemetryMessage, ...]) -> None:
        """Capture delivered telemetry."""
        self.messages.extend(messages)


def test_weather_observation_flows_through_cloud_bridge() -> None:
    """Weather telemetry should cross the cloud abstraction unchanged."""
    observation = WeatherObservation(
        timestamp=datetime(2026, 10, 5, 12, 0, tzinfo=UTC),
        temperature_c=21.5,
        relative_humidity_percent=55.0,
    )
    sink = CapturingSink()
    bridge = CloudTelemetryBridge(sink, batch_size=1)

    delivered = bridge.enqueue(weather_telemetry("pi-01", observation))

    assert delivered == 1
    assert sink.messages[0].device_id == "pi-01"
    assert sink.messages[0].event == "weather_observation"
    assert sink.messages[0].data["temperature_c"] == 21.5
