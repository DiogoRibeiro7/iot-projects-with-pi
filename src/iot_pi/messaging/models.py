"""Typed MQTT message models and JSON serialization."""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class TelemetryMessage:
    """Generic telemetry envelope."""

    device_id: str
    event: str
    timestamp: datetime
    data: dict[str, Any]
    schema_version: str = "1.0"

    def to_json(self) -> str:
        """Serialize the message using an explicit stable schema."""
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.astimezone(UTC).isoformat()
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, payload: str) -> "TelemetryMessage":
        """Parse and validate a serialized telemetry envelope."""
        raw = json.loads(payload)
        if not isinstance(raw, dict):
            raise ValueError("telemetry payload must be a JSON object")

        device_id = raw.get("device_id")
        event = raw.get("event")
        timestamp = raw.get("timestamp")
        data = raw.get("data")
        schema_version = raw.get("schema_version", "1.0")

        if not isinstance(device_id, str) or not device_id.strip():
            raise ValueError("device_id must be a non-empty string")
        if not isinstance(event, str) or not event.strip():
            raise ValueError("event must be a non-empty string")
        if not isinstance(timestamp, str):
            raise ValueError("timestamp must be an ISO-8601 string")
        if not isinstance(data, dict):
            raise ValueError("data must be a JSON object")
        if schema_version != "1.0":
            raise ValueError("unsupported telemetry schema_version")

        parsed = datetime.fromisoformat(timestamp)
        if parsed.tzinfo is None:
            raise ValueError("timestamp must include a timezone")

        return cls(
            device_id=device_id,
            event=event,
            timestamp=parsed,
            data=data,
            schema_version=schema_version,
        )


@dataclass(frozen=True, slots=True)
class CommandMessage:
    """Typed actuator command envelope."""

    device_id: str
    command: str
    timestamp: datetime

    @classmethod
    def from_json(cls, payload: str) -> "CommandMessage":
        """Parse and validate a JSON command."""
        raw = json.loads(payload)
        if not isinstance(raw, dict):
            raise ValueError("command payload must be a JSON object")

        device_id = raw.get("device_id")
        command = raw.get("command")
        timestamp = raw.get("timestamp")

        if not isinstance(device_id, str) or not device_id.strip():
            raise ValueError("device_id must be a non-empty string")
        if command not in {"auto", "on", "off"}:
            raise ValueError("command must be one of: auto, on, off")
        if not isinstance(timestamp, str):
            raise ValueError("timestamp must be an ISO-8601 string")

        parsed = datetime.fromisoformat(timestamp)
        if parsed.tzinfo is None:
            raise ValueError("timestamp must include a timezone")

        return cls(
            device_id=device_id,
            command=command,
            timestamp=parsed,
        )
