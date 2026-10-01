"""Weather telemetry serialization helpers."""

from iot_pi.messaging.models import TelemetryMessage
from iot_pi.messaging.topics import telemetry_topic
from iot_pi.weather.models import WeatherObservation


def weather_message(
    device_id: str,
    observation: WeatherObservation,
) -> tuple[str, str]:
    """Build topic and payload for one weather observation."""
    message = TelemetryMessage(
        device_id=device_id,
        event="weather_observation",
        timestamp=observation.timestamp,
        data={
            "temperature_c": observation.temperature_c,
            "relative_humidity_percent": observation.relative_humidity_percent,
            "pressure_hpa": observation.pressure_hpa,
        },
    )
    return telemetry_topic(device_id, "weather"), message.to_json()
