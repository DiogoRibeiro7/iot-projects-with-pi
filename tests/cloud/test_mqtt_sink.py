"""Tests for the reference MQTT cloud telemetry sink."""

from datetime import UTC, datetime
from typing import Any

import pytest

from iot_pi.cloud.mqtt import MqttCloudTelemetrySink
from iot_pi.messaging.models import TelemetryMessage


class FakePublisher:
    """Paho-compatible publisher test double."""

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.opened = False
        self.closed = False
        self.messages: list[tuple[str, str, int, bool]] = []

    def open(self) -> None:
        self.opened = True

    def close(self) -> None:
        self.closed = True

    def publish(
        self,
        topic: str,
        payload: str,
        *,
        qos: int,
        retain: bool,
    ) -> None:
        self.messages.append((topic, payload, qos, retain))


def telemetry() -> TelemetryMessage:
    """Create deterministic telemetry for sink tests."""
    return TelemetryMessage(
        device_id="pi-01",
        event="weather_observation",
        timestamp=datetime(2026, 10, 5, 12, 0, tzinfo=UTC),
        data={"temperature_c": 21.5},
    )


def test_mqtt_cloud_sink_publishes_device_scoped_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cloud MQTT topics should include device and event identifiers."""
    fake = FakePublisher()
    monkeypatch.setattr(
        "iot_pi.cloud.mqtt.PahoMqttPublisher",
        lambda *_args, **_kwargs: fake,
    )
    sink = MqttCloudTelemetrySink("example.invalid", topic_prefix="/fleet/")

    sink.open()
    sink.send_batch([telemetry()])
    sink.close()

    assert fake.opened is True
    assert fake.closed is True
    topic, payload, qos, retain = fake.messages[0]
    assert topic == "fleet/pi-01/telemetry/weather_observation"
    assert '"temperature_c":21.5' in payload
    assert qos == 1
    assert retain is False


@pytest.mark.parametrize(
    ("host", "topic_prefix", "qos"),
    [("", "devices", 1), ("example", "/", 1), ("example", "devices", 3)],
)
def test_mqtt_cloud_sink_rejects_invalid_configuration(
    host: str,
    topic_prefix: str,
    qos: int,
) -> None:
    """Reference sink configuration should fail early."""
    with pytest.raises(ValueError):
        MqttCloudTelemetrySink(
            host,
            topic_prefix=topic_prefix,
            qos=qos,
        )
