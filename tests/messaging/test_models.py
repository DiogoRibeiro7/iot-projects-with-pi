"""Tests for typed messaging models."""

import json
from datetime import UTC, datetime

import pytest

from iot_pi.messaging.models import CommandMessage, TelemetryMessage


def test_telemetry_message_serializes_stable_schema() -> None:
    """Telemetry JSON should retain device, event, timestamp, and data."""
    message = TelemetryMessage(
        device_id="pi-01",
        event="weather_observation",
        timestamp=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        data={"temperature_c": 21.5},
    )

    raw = json.loads(message.to_json())

    assert raw["device_id"] == "pi-01"
    assert raw["event"] == "weather_observation"
    assert raw["data"]["temperature_c"] == 21.5
    assert raw["timestamp"].endswith("+00:00")


def test_command_message_parses_valid_payload() -> None:
    """A valid override command should round-trip into a typed model."""
    command = CommandMessage.from_json(
        '{"device_id":"pi-01","command":"off","timestamp":"2026-10-01T12:00:00+00:00"}'
    )

    assert command.device_id == "pi-01"
    assert command.command == "off"


@pytest.mark.parametrize(
    "payload",
    [
        "[]",
        '{"device_id":"","command":"off","timestamp":"2026-10-01T12:00:00+00:00"}',
        '{"device_id":"pi-01","command":"invalid","timestamp":"2026-10-01T12:00:00+00:00"}',
        '{"device_id":"pi-01","command":"off","timestamp":"2026-10-01T12:00:00"}',
    ],
)
def test_command_message_rejects_invalid_payload(payload: str) -> None:
    """Malformed or unsupported commands must be rejected."""
    with pytest.raises(ValueError):
        CommandMessage.from_json(payload)
