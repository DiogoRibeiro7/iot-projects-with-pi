"""Tests for broker-independent application messaging."""

import json
from datetime import UTC, datetime

from iot_pi.hardware.fake import FakeDigitalInput, FakeDigitalOutput
from iot_pi.home.rules import AutomationPolicy
from iot_pi.home.service import HomeAutomationController, OverrideMode
from iot_pi.messaging.fake import InMemoryPublisher
from iot_pi.messaging.home import apply_override_command
from iot_pi.messaging.weather import weather_message
from iot_pi.weather.models import WeatherObservation
from iot_pi.weather.sensors import SimulatedTemperatureHumiditySensor


def test_weather_observation_builds_mqtt_ready_message() -> None:
    """Weather observations should map to a stable MQTT topic and payload."""
    publisher = InMemoryPublisher()
    observation = WeatherObservation(
        timestamp=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        temperature_c=21.5,
        relative_humidity_percent=54.0,
    )
    topic, payload = weather_message("pi-01", observation)

    publisher.publish(topic, payload, qos=1)

    assert publisher.messages[0].topic == "iot/pi-01/telemetry/weather"
    assert json.loads(publisher.messages[0].payload)["data"]["temperature_c"] == 21.5


def test_home_controller_accepts_typed_override_command() -> None:
    """A command message should update the controller without broker coupling."""
    controller = HomeAutomationController(
        SimulatedTemperatureHumiditySensor(),
        FakeDigitalInput(state=True),
        FakeDigitalOutput(),
        policy=AutomationPolicy(),
    )
    payload = (
        '{"device_id":"pi-01","command":"off",'
        '"timestamp":"2026-10-01T12:00:00+00:00"}'
    )

    command = apply_override_command(controller, payload, device_id="pi-01")

    assert command.command == "off"
    assert controller._override is OverrideMode.FORCE_OFF
