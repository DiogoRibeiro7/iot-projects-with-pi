"""Contract tests for versioned telemetry JSON schemas."""

import json
from datetime import UTC, datetime
from pathlib import Path

from iot_pi.messaging.models import TelemetryMessage


def test_telemetry_message_emits_schema_version() -> None:
    """Serialized telemetry must carry an explicit contract version."""
    message = TelemetryMessage(
        device_id="pi-01",
        event="weather_observation",
        timestamp=datetime(2026, 10, 6, 12, 0, tzinfo=UTC),
        data={"temperature_c": 21.5},
    )

    raw = json.loads(message.to_json())

    assert raw["schema_version"] == "1.0"


def test_legacy_payload_without_schema_version_is_accepted() -> None:
    """Existing persisted envelopes remain readable as schema version 1.0."""
    message = TelemetryMessage.from_json(
        '{"device_id":"pi-01","event":"weather_observation",'
        '"timestamp":"2026-10-06T12:00:00+00:00",'
        '"data":{"temperature_c":21.5}}'
    )

    assert message.schema_version == "1.0"


def test_committed_telemetry_schemas_define_versioned_contracts() -> None:
    """Committed schemas must require the common versioned envelope fields."""
    base = json.loads(
        Path("schemas/telemetry-envelope.schema.json").read_text(encoding="utf-8")
    )
    weather = json.loads(
        Path("schemas/weather-observation.schema.json").read_text(encoding="utf-8")
    )
    irrigation = json.loads(
        Path("schemas/irrigation-observation.schema.json").read_text(encoding="utf-8")
    )

    assert set(base["required"]) == {
        "schema_version",
        "device_id",
        "event",
        "timestamp",
        "data",
    }
    assert base["properties"]["schema_version"]["const"] == "1.0"
    assert weather["allOf"][1]["properties"]["event"]["const"] == "weather_observation"
    assert (
        irrigation["allOf"][1]["properties"]["event"]["const"]
        == "irrigation_observation"
    )
