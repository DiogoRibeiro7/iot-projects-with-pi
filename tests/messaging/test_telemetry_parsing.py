"""Tests for TelemetryMessage JSON parsing."""

from datetime import UTC, datetime

import pytest

from iot_pi.messaging.models import TelemetryMessage


def test_telemetry_message_round_trips_json() -> None:
    """Serialized telemetry should reconstruct the same envelope."""
    original = TelemetryMessage(
        device_id="pi-01",
        event="weather",
        timestamp=datetime(2026, 10, 5, 12, 0, tzinfo=UTC),
        data={"temperature_c": 21.5},
    )

    restored = TelemetryMessage.from_json(original.to_json())

    assert restored == original


@pytest.mark.parametrize(
    "payload",
    [
        "[]",
        '{"device_id":"","event":"weather","timestamp":"2026-10-05T12:00:00+00:00","data":{}}',
        '{"device_id":"pi","event":"","timestamp":"2026-10-05T12:00:00+00:00","data":{}}',
        '{"device_id":"pi","event":"weather","timestamp":1,"data":{}}',
        '{"device_id":"pi","event":"weather","timestamp":"2026-10-05T12:00:00","data":{}}',
        '{"device_id":"pi","event":"weather","timestamp":"2026-10-05T12:00:00+00:00","data":[]}',
    ],
)
def test_telemetry_message_rejects_invalid_json_schema(payload: str) -> None:
    """Malformed telemetry should fail before it enters durable storage."""
    with pytest.raises(ValueError):
        TelemetryMessage.from_json(payload)
