"""Persistent deployment identity and metadata."""

from __future__ import annotations

import json
import tomllib
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class DeviceMetadata:
    """Stable identity and deployment metadata for one device."""

    device_id: str
    hardware_class: str
    environment: str
    site: str
    software_version: str
    deployed_at: datetime

    def __post_init__(self) -> None:
        """Validate metadata invariants."""
        for name, value in (
            ("device_id", self.device_id),
            ("hardware_class", self.hardware_class),
            ("environment", self.environment),
            ("site", self.site),
            ("software_version", self.software_version),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be empty")
        if self.deployed_at.tzinfo is None:
            raise ValueError("deployed_at must include a timezone")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready metadata mapping."""
        payload = asdict(self)
        payload["deployed_at"] = self.deployed_at.isoformat()
        return payload

    def to_json(self) -> str:
        """Serialize metadata deterministically."""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


def load_device_metadata(path: Path) -> DeviceMetadata:
    """Load and validate deployment metadata from a TOML file."""
    with path.open("rb") as stream:
        raw = tomllib.load(stream)

    allowed = {
        "device_id",
        "hardware_class",
        "environment",
        "site",
        "software_version",
        "deployed_at",
    }
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"unknown device metadata keys: {', '.join(unknown)}")

    missing = sorted(allowed - set(raw))
    if missing:
        raise ValueError(f"missing device metadata keys: {', '.join(missing)}")

    deployed_at = raw["deployed_at"]
    if not isinstance(deployed_at, datetime):
        raise ValueError("deployed_at must be a TOML offset date-time")

    text_fields = {
        name: raw[name]
        for name in (
            "device_id",
            "hardware_class",
            "environment",
            "site",
            "software_version",
        )
    }
    for name, value in text_fields.items():
        if not isinstance(value, str):
            raise ValueError(f"{name} must be a string")

    return DeviceMetadata(
        device_id=text_fields["device_id"],
        hardware_class=text_fields["hardware_class"],
        environment=text_fields["environment"],
        site=text_fields["site"],
        software_version=text_fields["software_version"],
        deployed_at=deployed_at,
    )


def validate_device_id(expected: str, metadata: DeviceMetadata) -> None:
    """Require runtime identity to match persistent deployment identity."""
    if expected != metadata.device_id:
        raise ValueError(
            "runtime device_id does not match persistent device metadata: "
            f"{expected!r} != {metadata.device_id!r}"
        )
